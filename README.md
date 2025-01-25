## Dragonfly Backup Script

Yet another backup script doing it's thing as per backup.config file which contains sections listing files to backup, whereto backup and what files to exclude from backing up. 
Relies on tar on the backend with flags -z to output a compressed tar file at the destination.
Destination (specified in backup.config) will contain the N most recent backup tar files. N is specifed in the backup.config as well.
All paths in backup.config are to be set as absolute. Script takes care to alter them to fit the tar command.

### Installation
```bash
./install.sh

