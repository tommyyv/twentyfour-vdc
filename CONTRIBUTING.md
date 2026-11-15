```text
NOTE: KEY_ID can be retrieved from by running: gpg --list-keys

gpg --armor --sign WAIVER
gpg --armor --export KEY_ID > waivers/name-public-key.asc
gpg --import waivers/name-public-key.asc
gpg --verify waivers/WAIVER.asc

- NAME
  Waiver: waivers/name-waiver.asc
  Public key: waivers/name-public-key.asc
```
