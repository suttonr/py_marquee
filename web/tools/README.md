# PyMarquee Deployment Tools

Deployment tools for PyMarquee, including OCI Security List management and other deployment utilities.

## Installation

```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

## Tools

### OCI Security List Manager

Manages OCI Security List ingress rules based on IP allowlists from authentication files.

```bash
# Using environment variables
export OCI_COMPARTMENT_ID=ocid1.compartment.xxx
export OCI_SECURITY_LIST_ID=ocid1.securitylist.xxx
python -m tools.update_security_list

# Or use the console script entry point (after installation)
update-security-list --compartment-id ocid1.compartment.xxx --security-list-id ocid1.securitylist.xxx

# Dry run mode
update-security-list --compartment-id ocid1.compartment.xxx --security-list-id ocid1.securitylist.xxx --dry-run
```

#### Environment Variables

- `OCI_COMPARTMENT_ID`: OCID of the compartment containing the security list
- `OCI_SECURITY_LIST_ID`: OCID of the security list to manage
- `OCI_TCP_PORT`: Destination port for ingress rules (default: 8883)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
```
