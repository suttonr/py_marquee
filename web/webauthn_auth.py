"""
WebAuthn/FIDO2 authentication module for Marquee Control
Provides WebAuthn registration and authentication endpoints
"""
import os
import json
import secrets
from flask import request, jsonify, session
from fido2.server import Fido2Server
from fido2 import webauthn
from fido2.utils import websafe_encode, websafe_decode
import base64

class WebAuthnManager:
    """Manages WebAuthn/FIDO2 authentication"""
    
    def __init__(self, rp_id, rp_name, rp_host, credentials_file):
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.rp_host = rp_host
        self.credentials_file = credentials_file
        self.credentials = self._load_credentials()
        
        # Create FIDO2 server
        self.server = Fido2Server(
            rp={"id": rp_id, "name": rp_name},
            attestation="none",
        )
        
        # Generate challenge
        self.challenge = secrets.token_bytes(32)
    
    def _load_credentials(self):
        """Load stored WebAuthn credentials"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading credentials: {e}")
        return {}
    
    def _save_credentials(self):
        """Save WebAuthn credentials to file"""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(self.credentials, f)
        except Exception as e:
            print(f"Error saving credentials: {e}")
    
    def _serialize_options(self, obj):
        """Convert fido2 options to JSON-serializable dictionary"""
        if isinstance(obj, dict):
            return {k: self._serialize_options(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_options(v) for v in obj]
        elif isinstance(obj, bytes):
            # WebAuthn expects base64url encoding without padding
            return base64.urlsafe_b64encode(obj).decode('utf-8').rstrip('=')
        elif hasattr(obj, 'items'):
            return {k: self._serialize_options(v) for k, v in obj.items()}
        elif hasattr(obj, 'value'): # Enum
            return obj.value
        else:
            return obj

    def get_registration_options(self, username):
        """
        Generate WebAuthn registration options for a new credential
        """
        try:
            # Generate a new challenge
            challenge = secrets.token_bytes(32)
            session['webauthn_challenge'] = challenge
            session['webauthn_username'] = username
            
            # Get existing credentials for this user to exclude
            user_credentials = self.credentials.get(username, [])
            
            # Build user entity
            user = {
                "id": username.encode('utf-8'),
                "name": username,
                "displayName": username
            }
            
            # Build registration options
            options, state = self.server.register_begin(
                user=user,
                credentials=None,  # We handle credential exclusion on client side
                challenge=challenge,
                authenticator_attachment=None,  # Allow both platform and cross-platform authenticators
                user_verification="preferred",
            )
            
            # Store state for verification
            session['webauthn_state'] = state
            
            # Serialize options - convert bytes to base64
            serialized_options = self._serialize_options(options)
            
            return jsonify(serialized_options), 200
        except Exception as e:
            print(f"Error generating registration options: {e}")
            return jsonify({'error': str(e)}), 500
    
    def verify_registration(self, username, attestation_response):
        """
        Verify and store a new WebAuthn credential
        """
        try:
            # Get stored state
            state = session.get('webauthn_state')
            stored_username = session.get('webauthn_username')
            
            if not state or stored_username != username:
                return jsonify({'error': 'Invalid state'}), 400
            
            # Parse the attestation response - get raw bytes from base64url
            # Add padding if needed
            def decode_b64url(s):
                return base64.urlsafe_b64decode(s + '=' * (4 - len(s) % 4))

            attestation_bytes = decode_b64url(attestation_response['response']['attestationObject'])
            client_data_bytes = decode_b64url(attestation_response['response']['clientDataJSON'])
            
            # Create fido2 objects
            client_data = webauthn.CollectedClientData(client_data_bytes)
            attestation_object = webauthn.AttestationObject(attestation_bytes)
            
            # Verify the registration
            auth_data = self.server.register_complete(
                state=state,
                client_data=client_data,
                attestation_object=attestation_object,
            )
            
            # Store the credential
            credential_data = {
                'credential_id': base64.urlsafe_b64encode(auth_data.credential_data.credential_id).decode('utf-8').rstrip('='),
                'credential_data': base64.b64encode(bytes(auth_data.credential_data)).decode('utf-8'),
            }
            
            if username not in self.credentials:
                self.credentials[username] = []
            
            # Check if credential already exists
            for cred in self.credentials[username]:
                if cred['credential_id'] == credential_data['credential_id']:
                    return jsonify({'error': 'Credential already registered'}), 400
            
            self.credentials[username].append(credential_data)
            self._save_credentials()
            
            # Clear session
            session.pop('webauthn_challenge', None)
            session.pop('webauthn_username', None)
            session.pop('webauthn_state', None)
            
            return jsonify({'status': 'ok', 'message': 'Credential registered successfully'}), 200
        except Exception as e:
            print(f"Error verifying registration: {e}")
            return jsonify({'error': str(e)}), 500
    
    def get_authentication_options(self, username):
        """
        Generate WebAuthn authentication options
        """
        try:
            # Generate a new challenge
            challenge = secrets.token_bytes(32)
            session['webauthn_challenge'] = challenge
            session['webauthn_username'] = username
            
            # Get credentials for this user
            user_credentials = self.credentials.get(username, [])
            
            if not user_credentials:
                return jsonify({'error': 'No credentials found for user'}), 404
            
            # Build credential descriptors - decode base64url to bytes
            def decode_b64url(s):
                return base64.urlsafe_b64decode(s + '=' * (4 - len(s) % 4))
                
            cred_descriptors = []
            for cred in user_credentials:
                cred_id = decode_b64url(cred['credential_id'])
                cred_descriptors.append(
                    webauthn.PublicKeyCredentialDescriptor(
                        type="public-key",
                        id=cred_id,
                        transports=["usb", "nfc", "ble", "internal", "hybrid"]  # Include FIDO2 key transports
                    )
                )
            
            # Build authentication options
            options, state = self.server.authenticate_begin(
                credentials=cred_descriptors,
                challenge=challenge,
                user_verification="preferred",
            )
            
            # Store state
            session['webauthn_state'] = state
            
            # Serialize options - convert bytes to base64
            serialized_options = self._serialize_options(options)
            
            return jsonify(serialized_options), 200
        except Exception as e:
            print(f"Error generating authentication options: {e}")
            return jsonify({'error': str(e)}), 500
    
    def verify_authentication(self, username, credential_id, authenticator_response):
        """
        Verify WebAuthn authentication
        """
        try:
            # Get stored state
            state = session.get('webauthn_state')
            stored_username = session.get('webauthn_username')

            if not state or stored_username != username:
                return jsonify({'error': 'Invalid state'}), 400

            # Get user credentials
            user_credentials = self.credentials.get(username, [])

            if not user_credentials:
                return jsonify({'error': 'No credentials found for user'}), 404

            # Find the matching credential
            matching_cred = None
            for cred in user_credentials:
                if cred['credential_id'] == credential_id:
                    matching_cred = cred
                    break

            if not matching_cred:
                return jsonify({'error': 'Credential not found'}), 404

            # Parse the authenticator response - get raw bytes from base64url
            def decode_b64url(s):
                return base64.urlsafe_b64decode(s + '=' * (4 - len(s) % 4))

            client_data_bytes = decode_b64url(authenticator_response['clientDataJSON'])
            authenticator_data_bytes = decode_b64url(authenticator_response['authenticatorData'])
            signature = decode_b64url(authenticator_response['signature'])
            user_handle = None
            if authenticator_response.get('userHandle'):
                user_handle = decode_b64url(authenticator_response['userHandle'])

            # Create fido2 objects
            client_data = webauthn.CollectedClientData(client_data_bytes)
            authenticator_data = webauthn.AuthenticatorData(authenticator_data_bytes)

            print(f"DEBUG auth: client_data type={type(client_data)}")
            print(f"DEBUG auth: authenticator_data type={type(authenticator_data)}")

            # Verify the authentication using server
            # We need to pass the credential ID
            cred_id = decode_b64url(credential_id)

            # Reconstruct all AttestedCredentialData for the user
            attested_creds = []
            for cred in user_credentials:
                cred_data_bytes = base64.b64decode(cred['credential_data'])
                attested_cred = webauthn.AttestedCredentialData(cred_data_bytes)
                attested_creds.append(attested_cred)

            # In fido2 1.1.0+, authenticate_complete expects a list of AttestedCredentialData
            # for all allowed credentials
            self.server.authenticate_complete(
                state=state,
                credentials=attested_creds,
                credential_id=cred_id,
                client_data=client_data,
                auth_data=authenticator_data,
                signature=signature,
            )

            # Clear session
            session.pop('webauthn_challenge', None)
            session.pop('webauthn_username', None)
            session.pop('webauthn_state', None)

            return jsonify({'status': 'ok', 'message': 'Authentication successful'}), 200
        except Exception as e:
            print(f"Error verifying authentication: {e}")
            return jsonify({'error': str(e)}), 500
    
    def has_credentials(self, username):
        """Check if user has WebAuthn credentials registered"""
        return username in self.credentials and len(self.credentials[username]) > 0
    
    def remove_credentials(self, username):
        """Remove all credentials for a user"""
        if username in self.credentials:
            del self.credentials[username]
            self._save_credentials()
            return True
        return False

    def get_users(self):
        """Get list of registered users with their credential counts"""
        users = []
        for username, credentials in self.credentials.items():
            users.append({
                'username': username,
                'credential_count': len(credentials),
                'has_credentials': len(credentials) > 0
            })
        return users

    def get_rp_config(self):
        """Get the relying party configuration"""
        return {
            'rp_id': self.rp_id,
            'rp_name': self.rp_name,
            'rp_host': self.rp_host
        }
