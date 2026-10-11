import os, base64, re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENV_FILE = ".env"
IN_FILE = "db/enrollments.txt"
OUT_FILE = "db/enrollments_encrypted.sql"


def load_env(path):
    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v
    return env


def make_encryptor(key):
    def enc(text):
        nonce = os.urandom(12)
        ct = AESGCM(key).encrypt(nonce, text.encode("utf-8"), None)
        return base64.b64encode(nonce + ct).decode()
    return enc


def main():
    env = load_env(ENV_FILE)
    key = base64.b64decode(env["AES_KEY"])
    assert len(key) == 32, f"key must be 32 bytes, got {len(key)}"

    enc = make_encryptor(key)

    with open(IN_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    out = []
    count = 0
    for line in lines:
        if "notes" in line and "VALUES" in line:
            m = re.search(
                r"(.*VALUES\s*\([^)]*?,\s*')([^']*)('\);?\s*)$", line
            )
            if m:
                pre, comment, post = m.groups()
                line = pre + enc(comment) + post
                count += 1
        out.append(line)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print(f"Done: {OUT_FILE}  ({count} comments encrypted)")


if __name__ == "__main__":
    main()