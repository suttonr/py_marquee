#!/usr/bin/env python3
"""
OCI Security List Ingress Rule Manager

This script manages OCI Security List ingress rules based on IP allowlists
from web/auth/*.json files. It uses instance principal for authentication.

Usage:
    python update_security_list.py --compartment-id <OCID> --security-list-id <OCID> [--dry-run]
    python update_security_list.py --dry-run  # Uses environment variables

Environment Variables (or command line arguments):
    OCI_COMPARTMENT_ID: OCID of the compartment containing the security list
    OCI_SECURITY_LIST_ID: OCID of the security list to manage
    OCI_TCP_PORT: Destination port for the ingress rules (default: 8883)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Set, List, Dict, Any

# OCI SDK imports
try:
    import oci
    from oci.core import VirtualNetworkClient
    from oci.core.models import (
        IngressSecurityRule,
        UpdateSecurityListDetails,
        TcpOptions,
        PortRange,
    )
    # Try to import the instance principal signer - different versions use different paths
    # Try the newer name first, then the older one
    try:
        from oci.auth.signers import InstancePrincipalsSecurityTokenSigner as Signer
    except ImportError:
        try:
            from oci.auth.signers.instance_principal_signer import InstancePrincipalsSecurityTokenSigner as Signer
        except ImportError:
            try:
                from oci.auth.signers import InstancePrincipalSigner as Signer
            except ImportError:
                try:
                    from oci.auth.signers.instance_principal_signer import InstancePrincipalSigner as Signer
                except ImportError:
                    Signer = None
except ImportError:
    print("ERROR: OCI SDK not installed. Install with: pip install oci")
    sys.exit(1)


# Configuration
AUTH_DIR = Path("/home/opc/web/auth")
CACHE_FILE = Path("/var/tmp/update_security_list_cache.json")

# Template for ingress rules - can be customized
INGRESS_RULE_TEMPLATE = {
    "protocol": "6",  # TCP
    "source": None,  # Will be set to the IP
    "source_type": "CIDR_BLOCK",
    "tcp_options": {
        "destination_port_range": {
            "min": None,  # Will be set to the port
            "max": None,  # Will be set to the port
        }
    },
    "is_stateless": False,
}


def load_user_allowlist(auth_dir: Path) -> Set[str]:
    """
    Load all IP addresses from the mqtt_allowlist key in all JSON files
    in the auth directory.
    
    Args:
        auth_dir: Path to the auth directory containing JSON files
        
    Returns:
        Set of IP addresses from all user's mqtt_allowlist
    """
    allowlist = set()
    
    if not auth_dir.exists():
        print(f"WARNING: Auth directory {auth_dir} does not exist")
        return allowlist
    
    # Find all JSON files in the auth directory
    json_files = list(auth_dir.glob("*.json"))
    
    if not json_files:
        print(f"WARNING: No JSON files found in {auth_dir}")
        return allowlist
    
    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
            
            # Get mqtt_allowlist from each file
            mqtt_allowlist = data.get("mqtt_allowlist", [])
            
            for ip in mqtt_allowlist:
                if ip:  # Skip empty strings
                    allowlist.add(ip)
                    
            print(f"Loaded {len(mqtt_allowlist)} IPs from {json_file.name}: {mqtt_allowlist}")
            
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse {json_file}: {e}")
        except Exception as e:
            print(f"ERROR: Failed to read {json_file}: {e}")
    
    return allowlist


def get_current_ingress_ips(security_list: Dict[str, Any]) -> Set[str]:
    """
    Extract the source IP addresses from all TCP ingress rules in the security list.
    
    Args:
        security_list: The security list dictionary from OCI
        
    Returns:
        Set of source IP addresses from TCP ingress rules
    """
    current_ips = set()
    
    ingress_rules = security_list.get("ingress_security_rules", [])
    
    for rule in ingress_rules:
        # Only look at TCP rules (protocol = "6")
        if rule.get("protocol") == "6":
            source = rule.get("source")
            if source:
                current_ips.add(source)
    
    return current_ips


def create_ingress_rule(ip: str, port: int) -> IngressSecurityRule:
    """
    Create an IngressSecurityRule with the proper OCI model objects.
    
    Args:
        ip: The source IP address (CIDR format)
        port: The destination port
        
    Returns:
        IngressSecurityRule object
    """
    # Create the port range object
    port_range = PortRange(min=port, max=port)
    
    # Create the TCP options object
    tcp_options = TcpOptions(destination_port_range=port_range)
    
    # Create and return the ingress security rule
    return IngressSecurityRule(
        protocol="6",  # TCP
        source=ip,
        source_type="CIDR_BLOCK",
        tcp_options=tcp_options,
        is_stateless=False,
    )


def get_ingress_rules_for_ips(ips: Set[str], port: int) -> List[IngressSecurityRule]:
    """
    Create IngressSecurityRule objects for all given IPs.
    
    Args:
        ips: Set of IP addresses
        port: Destination port
        
    Returns:
        List of IngressSecurityRule objects
    """
    return [create_ingress_rule(ip, port) for ip in ips]


def load_cache(cache_file: Path) -> Dict[str, Any]:
    """
    Load the cached allowlist state from a file.
    
    Args:
        cache_file: Path to the cache file
        
    Returns:
        Dictionary with cached data or empty dict if no cache exists
    """
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load cache: {e}")
    return {}


def save_cache(cache_file: Path, user_allowlist: Set[str], port: int) -> None:
    """
    Save the current allowlist state to a cache file.
    
    Args:
        cache_file: Path to the cache file
        user_allowlist: Set of IP addresses currently in the allowlist
        port: The port being managed
    """
    try:
        cache_data = {
            "allowlist": sorted(list(user_allowlist)),
            "port": port,
        }
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)
        print(f"Cache saved to {cache_file}")
    except IOError as e:
        print(f"Warning: Failed to save cache: {e}")


def check_update_needed(
    user_allowlist: Set[str],
    port: int,
    cache: Dict[str, Any],
) -> bool:
    """
    Check if an update is needed by comparing current allowlist with cached state.
    
    Args:
        user_allowlist: Set of IP addresses currently in the allowlist
        port: The port being managed
        cache: Cached data from previous run
        
    Returns:
        True if update is needed, False if no changes
    """
    cached_allowlist = set(cache.get("allowlist", []))
    cached_port = cache.get("port")
    
    # Check if allowlist or port has changed
    if user_allowlist != cached_allowlist or port != cached_port:
        if not cached_allowlist:
            print("\nNo previous cache found - update required")
        elif user_allowlist != cached_allowlist:
            print("\nAllowlist has changed - update required")
            print(f"  Previous: {cached_allowlist}")
            print(f"  Current:  {user_allowlist}")
        else:
            print("\nPort has changed - update required")
        return True
    
    print("\nNo changes detected - skipping OCI update")
    return False


def update_security_list(
    vnc_client: VirtualNetworkClient,
    compartment_id: str,
    security_list_id: str,
    user_allowlist: Set[str],
    port: int,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Update the security list ingress rules to match the user allowlist.
    
    Args:
        vnc_client: The OCI VirtualNetworkClient
        compartment_id: The OCID of the compartment
        security_list_id: The OCID of the security list
        user_allowlist: Set of IPs that should be allowed
        port: The destination port for the rules
        dry_run: If True, only print what would be done
        
    Returns:
        Dictionary with summary of changes
    """
    # Get current security list
    print(f"\nFetching security list {security_list_id}...")
    security_list = vnc_client.get_security_list(security_list_id).data
    security_list_dict = security_list.__dict__
    
    # Get etag for concurrency control
    etag = getattr(security_list, "etag", None) or getattr(security_list, "_etag", None) or getattr(security_list, "e_tag", None)
    print(f"Current etag: {etag}")
    
    # Get current ingress IPs
    current_ips = get_current_ingress_ips(security_list_dict)
    print(f"Current ingress IPs: {current_ips}")
    
    # Determine what needs to be added and removed
    ips_to_add = user_allowlist - current_ips
    ips_to_remove = current_ips - user_allowlist
    
    print(f"\nUser allowlist: {user_allowlist}")
    print(f"IPs to ADD: {ips_to_add}")
    print(f"IPs to REMOVE: {ips_to_remove}")
    
    if dry_run:
        print("\n[DRY RUN] No changes will be made")
        return {
            "dry_run": True,
            "ips_to_add": list(ips_to_add),
            "ips_to_remove": list(ips_to_remove),
        }
    
    if not ips_to_add and not ips_to_remove:
        print("\nNo changes needed - security list is up to date")
        return {"dry_run": False, "changes": "none"}
    
    # Build the new ingress rules list
    # Keep existing rules that are NOT in ips_to_remove
    new_ingress_rules = []
    
    for rule in security_list_dict.get("ingress_security_rules", []):
        source = rule.get("source")
        # Keep the rule if:
        # 1. It's not a TCP rule, OR
        # 2. It's a TCP rule but the source IP is in user_allowlist
        if rule.get("protocol") != "6" or source in user_allowlist:
            new_ingress_rules.append(rule)
    
    # Add new rules for IPs that need to be added
    new_rules = get_ingress_rules_for_ips(ips_to_add, port)
    new_ingress_rules.extend(new_rules)
    
    # Prepare update request with etag for concurrency control
    update_details = UpdateSecurityListDetails(
        ingress_security_rules=new_ingress_rules
    )
    
    try:
        # Update with retry logic for etag conflicts
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"\nUpdating security list (attempt {attempt + 1})...")
                response = vnc_client.update_security_list(
                    security_list_id=security_list_id,
                    update_security_list_details=update_details,
                    if_match=etag,
                )
                print(f"Security list updated successfully!")
                # Get etag from response using same pattern as above
                new_etag = getattr(response.data, "etag", None) or getattr(response.data, "_etag", None) or getattr(response.data, "e_tag", None)
                print(f"New etag: {new_etag}")
                
                return {
                    "dry_run": False,
                    "ips_added": list(ips_to_add),
                    "ips_removed": list(ips_to_remove),
                    "new_etag": new_etag,
                }
                
            except oci.exceptions.ServiceError as e:
                if e.status == 412:  # Precondition Failed - etag mismatch
                    print(f"ETag conflict, refreshing security list...")
                    # Get fresh security list
                    security_list = vnc_client.get_security_list(security_list_id).data
                    etag = getattr(security_list, "etag", None) or getattr(security_list, "_etag", None) or getattr(security_list, "e_tag", None)
                    update_details = UpdateSecurityListDetails(
                        ingress_security_rules=new_ingress_rules
                    )
                else:
                    raise
                    
        print("ERROR: Failed to update after multiple attempts")
        return {"dry_run": False, "error": "max_retries_exceeded"}
        
    except oci.exceptions.ServiceError as e:
        print(f"ERROR: Failed to update security list: {e}")
        raise


def create_vnc_client() -> VirtualNetworkClient:
    """
    Create an OCI VirtualNetworkClient using instance principal authentication.
    
    Returns:
        Configured VirtualNetworkClient
        
    Raises:
        Exception if authentication fails
    """
    # Check if we were able to import the signer
    if Signer is None:
        print("ERROR: Could not find instance principal signer in OCI SDK")
        print("Your OCI SDK version may be too old or the API has changed")
        raise ImportError("Instance principal signer not available")
    
    try:
        # Use instance principal authentication
        signer = Signer()
        
        # Try with empty config first (older SDK versions)
        try:
            vnc_client = VirtualNetworkClient(config={}, signer=signer)
        except TypeError:
            # If that doesn't work, try without config (newer versions)
            vnc_client = VirtualNetworkClient(signer=signer)
        
        print("Successfully authenticated using instance principal")
        return vnc_client
        
    except Exception as e:
        print(f"ERROR: Failed to authenticate with instance principal: {e}")
        print("Make sure this script is running on an OCI instance with appropriate IAM policy")
        raise



def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Manage OCI Security List ingress rules based on user allowlists"
    )
    parser.add_argument(
        "--compartment-id",
        type=str,
        default=os.environ.get("OCI_COMPARTMENT_ID"),
        help="OCID of the compartment containing the security list",
    )
    parser.add_argument(
        "--security-list-id",
        type=str,
        default=os.environ.get("OCI_SECURITY_LIST_ID"),
        help="OCID of the security list to manage",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("OCI_TCP_PORT", "8883")),
        help="Destination port for ingress rules (default: 8883)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    
    args = parser.parse_args()
    
    # Validate required arguments
    if not args.compartment_id:
        print("ERROR: --compartment-id is required (or OCI_COMPARTMENT_ID environment variable)")
        parser.print_help()
        sys.exit(1)
    
    if not args.security_list_id:
        print("ERROR: --security-list-id is required (or OCI_SECURITY_LIST_ID environment variable)")
        parser.print_help()
        sys.exit(1)
    
    print("=" * 60)
    print("OCI Security List Ingress Rule Manager")
    print("=" * 60)
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")
    
    # Load user allowlist from auth files
    print(f"Loading user allowlist from {AUTH_DIR}...")
    user_allowlist = load_user_allowlist(AUTH_DIR)
    print(f"Total unique IPs in allowlist: {len(user_allowlist)}")
    
    if not user_allowlist:
        print("WARNING: No IPs found in user allowlist")
        # Convert to CIDR format (each IP becomes /32)
        user_allowlist = {f"{ip}/32" for ip in user_allowlist}
    
    # Convert IPs to CIDR format if needed
    user_allowlist_cidr = set()
    for ip in user_allowlist:
        if "/" not in ip:
            user_allowlist_cidr.add(f"{ip}/32")
        else:
            user_allowlist_cidr.add(ip)
    
    print(f"User allowlist (CIDR format): {user_allowlist_cidr}")
    
    # Load cache to check if update is needed
    cache = load_cache(CACHE_FILE)
    
    # Check if update is needed before making any OCI API calls
    if not check_update_needed(user_allowlist_cidr, args.port, cache):
        # No changes - exit early without calling OCI
        print("\n" + "=" * 60)
        print("Summary:")
        print("=" * 60)
        print(json.dumps({"update_needed": False, "changes": "none"}, indent=2))
        return
    
    # Only create OCI client and authenticate if update is needed
    # Create OCI client with instance principal auth
    print("\nAuthenticating with OCI using instance principal...")
    vnc_client = create_vnc_client()
    
    # Update security list
    print("PORT:", args.port)
    result = update_security_list(
        vnc_client=vnc_client,
        compartment_id=args.compartment_id,
        security_list_id=args.security_list_id,
        user_allowlist=user_allowlist_cidr,
        port=args.port,
        dry_run=args.dry_run,
    )
    
    # Only save cache when actual changes were written to OCI (not dry-run)
    # This ensures the next run will see the change and update OCI accordingly
    if not args.dry_run and result.get("changes") != "none":
        save_cache(CACHE_FILE, user_allowlist_cidr, args.port)
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
