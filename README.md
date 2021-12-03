# tahoe-upload

Rsync-like file uploading program for Tahoe-LAFS. Also see [tahoe-pyfuse3](https://github.com/Derkades/tahoe-pyfuse3) for a Tahoe-LAFS FUSE mount client.

## Installation

### Native python

Install dependencies (debian):
```
apt install python3 python3-requests python3-tqdm
```

Run `python3 upload.py`

### Debian
The package `tahoe-upload` is available in [my repository](https://deb.rkslot.nl). If you run into missing dependency issues on older Debian/Ubuntu versions, use the `tahoe-upload-static` package instead (amd64 only).

To build these packages locally, run `./build-deb.sh`.

### Docker
The image `derkades/tahoe-upload` is available on Docker Hub.

Like `rsync`, the upload program can upload local files and directories to a Tahoe-LAFS directory.

## Usage
```
usage: upload.py [-h] path api cap

positional arguments:
  path        Path to file or directory to upload. Like rsync, add a trailing slash to upload directory contents, no trailing slash to upload the directory itself.
  api         HTTP REST API URL of a Tahoe-LAFS node
  cap         Tahoe directory capability where files should be uploaded to

optional arguments:
  -h, --help  show this help message and exit
```

Example:
```
python3 upload.py /some/dir http://localhost:3456 URI:DIR2:fzwyukltbehjx37nuyp6wy2qge:lzzg3oy2okmfcblquvoyp7qtq6xge2ptge6srogn56hbn7ckhgra
```

### Behavior
The upload script will recursively create directories and upload files in Tahoe-LAFS. Its duplicate file/directory behavior is best described using pseudocode:

```
if local is file:
    if remote is file:
        if remote and local file are same size:
            don't upload
        else:
            delete and re-upload
    else if remote is directory:
        delete directory and upload file
    else if remote doesn't exist:
        upload file
else if directory:
    if remote is file:
        delete file and create directory
    else if remote is directory:
        do nothing
    else if remote doesn't exist:
        create directory

    repeat for all files in this directory
```
The upload script will never move/delete/create/modify local files/directories.
