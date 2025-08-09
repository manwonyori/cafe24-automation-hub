#!/usr/bin/env python3
"""
Generate secure keys for Cafe24 Automation Hub
"""

import secrets
import string
from pathlib import Path

def generate_encryption_key():
    """Generate Fernet-compatible encryption key"""
    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        return key.decode()
    except ImportError:
        print("cryptography not installed, generating fallback key")
        # Generate 32-character key as fallback
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))

def generate_jwt_secret(length=64):
    """Generate JWT secret key"""
    alphabet = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def update_env_file():
    """Update .env file with generated keys"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Please copy .env.example to .env first")
        return False
    
    # Read current env file
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Generate new keys
    encryption_key = generate_encryption_key()
    jwt_secret = generate_jwt_secret()
    
    print("🔑 Generated new security keys:")
    print(f"Encryption Key: {encryption_key}")
    print(f"JWT Secret: {jwt_secret[:20]}...")
    
    # Update lines
    new_lines = []
    updated_encryption = False
    updated_jwt = False
    
    for line in lines:
        if line.startswith('ENCRYPTION_KEY='):
            if 'your_32_character_encryption_key_here' in line or not line.split('=', 1)[1].strip():
                new_lines.append(f'ENCRYPTION_KEY={encryption_key}\n')
                updated_encryption = True
            else:
                new_lines.append(line)
                print("⚠️ ENCRYPTION_KEY already set, not updating")
        elif line.startswith('JWT_SECRET='):
            if 'your_jwt_secret_key_here' in line or not line.split('=', 1)[1].strip():
                new_lines.append(f'JWT_SECRET={jwt_secret}\n')
                updated_jwt = True
            else:
                new_lines.append(line)
                print("⚠️ JWT_SECRET already set, not updating")
        else:
            new_lines.append(line)
    
    # Write updated file
    with open(env_file, 'w') as f:
        f.writelines(new_lines)
    
    if updated_encryption or updated_jwt:
        print("✅ .env file updated with new keys")
    
    return True

def main():
    """Main function"""
    print("🔐 Cafe24 Automation Hub - Key Generator")
    print("=" * 45)
    
    if update_env_file():
        print("\n✅ Setup complete!")
        print("\n⚠️ IMPORTANT:")
        print("1. Never commit the .env file to version control")
        print("2. Keep your keys secure")
        print("3. Set these keys in Render environment variables for deployment")
    else:
        print("\n❌ Setup failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())