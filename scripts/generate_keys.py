"""
Gera o par de chaves RSA para o bot.
Uso: uv run python scripts/generate_keys.py
"""

from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def main() -> None:
    keys_dir = Path("keys")
    keys_dir.mkdir(exist_ok=True)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    (keys_dir / "private.pem").write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    (keys_dir / "public.pem").write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    print("✓ keys/private.pem e keys/public.pem gerados com sucesso.")


if __name__ == "__main__":
    main()
