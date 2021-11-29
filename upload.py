#!/usr/bin/env python3
import sys
import requests
from typing import BinaryIO, Generator, Set, Dict, Tuple
from urllib.parse import quote
from pathlib import Path
from argparse import ArgumentParser
from tqdm import tqdm


# TODO make configurable through command flags
UPLOAD_BLOCK_SIZE = 512*1024
UPLOAD_PROGRESS_UNIT = 'bytes'
assert UPLOAD_BLOCK_SIZE > 0
assert UPLOAD_PROGRESS_UNIT in {'bytes', 'bits'}


def get_names_in_dircap(api: str, parent_cap: str) -> Dict[str, Tuple[str, bool, int]]:
    r = requests.get(f'{api}/uri/{quote(parent_cap)}?t=json',
                     headers={'Accept': 'text/plain'})
    assert r.status_code == 200
    (node_type, content) = r.json()
    assert node_type == 'dirnode'

    children = {}

    for child_name, child_content in content['children'].items():
        child_type = child_content[0]
        if child_type == 'dirnode':
            cap = child_content[1]['rw_uri']
            is_dir = True
            size = None
        elif child_type == 'filenode':
            cap = child_content[1]['ro_uri']
            is_dir = False
            size = child_content[1]['size'] if 'size' in child_content[1] else None
        else:
            raise Exception('Unsupported node type ' + child_type)

        children[child_name] = (cap, is_dir, size)

    return children


def file_reader(f: BinaryIO, bar: tqdm) -> Generator[bytes, None, None]:
    while True:
        data: bytes = f.read(UPLOAD_BLOCK_SIZE)
        if data:
            bar.update(len(data) * (8 if UPLOAD_PROGRESS_UNIT == 'bits' else 1))
            yield data
        else:
            break


def upload_file(path: Path, file_size: int, api: str, parent_cap: str, log_prefix: str) -> None:
    with open(path, 'rb') \
            as f, tqdm(desc=(log_prefix + path.name),
                       total=file_size * (8 if UPLOAD_PROGRESS_UNIT == 'bits' else 1),
                       unit='iB' if UPLOAD_PROGRESS_UNIT == 'bytes' else 'ib',
                       unit_scale=True,
                       unit_divisor=1024) as bar:
        r = requests.put(f'{api}/uri/{quote(parent_cap)}/{quote(path.name)}?format=CHK',
                         data=file_reader(f, bar),
                         headers={'Accept': 'text/plain'})

    if r.status_code == 201:
        print(log_prefix + path.name, 'done!')
    else:
        print(r.text)
        print(f'Failed to upload file {path}, status code {r.status_code}')
        exit(1)


def check_upload_file(path: Path, api: str, parent_cap: str, parent_contents: Dict[str, Tuple[str, bool, int]], log_prefix: str) -> None:
    # check if a file or directory with this name already exists
    print(log_prefix + path.name, end=': ')
    if path.name in parent_contents:
        print('already exists, ', end='', flush=True)
        (_cap, is_dir, size) = parent_contents[path.name]
        local_size = path.stat().st_size
        if not is_dir:
            if size is not None:
                if size == local_size:
                    print('same size')
                    return
                else:
                    print('different size', end=' ', flush=True)
            else:
                print('file has no size, mutable?', end=' ', flush=True)
        else:
            print('remote cap is a directory', end=' ', flush=True)

        print('deleting...', end=' ', flush=True)
        r = requests.delete(f'{api}/uri/{quote(parent_cap)}/{quote(path.name)}',
                            headers={'Accept': 'text/plain'})
        if r.status_code != 200:
            print('unexpected status code', r.status_code)
            print(r.text)
            exit(1)
        print('re-uploading...')
        upload_file(path, local_size, api, parent_cap, log_prefix)
    else:
        print('uploading...')
        upload_file(path, path.stat().st_size, api, parent_cap, log_prefix)


def upload_dir(path: Path, api: str, parent_cap: str, parent_contents: Dict[str, Tuple[str, bool, int]], log_prefix: str) -> None:
    print(log_prefix + path.name, end=': ')
    if path.name in parent_contents:
        (cap, is_dir, _size) = parent_contents[path.name]
        if not is_dir:
            print('not a directory in tahoe filesystem!')
            # TODO Delete remote file and create remote directory if not a dir
            exit(1)
        print('already exists, ', end='', flush=True)
    else:
        print('creating directory...', end=' ', flush=True)
        r = requests.post(f'{api}/uri/{quote(parent_cap)}/{quote(path.name)}?t=mkdir',
                          headers={'Accept': 'text/plain'})
        cap = r.text
        print('created,', end=' ', flush=True)

    print('uploading contents....')
    upload_contents(parent_path=path, api=api, parent_cap=cap, log_prefix=(log_prefix + '    '))


def upload_contents(parent_path: Path, api: str, parent_cap: str, log_prefix: str) -> None:
    parent_contents = get_names_in_dircap(api, parent_cap)

    for path in sorted(parent_path.iterdir()):
        if path.is_file():
            check_upload_file(path, api, parent_cap, parent_contents, log_prefix)
        elif path.is_dir():
            upload_dir(path, api, parent_cap, parent_contents, log_prefix)
        else:
            print(log_prefix + path.name, "skipping, unknown file type")


def main(path_str: str, api: str, cap: str) -> None:
    path = Path(path_str)
    if path_str.endswith('/'):
        upload_contents(path, api, cap, log_prefix='')
    else:
        parent_contents = get_names_in_dircap(api, cap)
        upload_dir(path, api, cap, parent_contents, log_prefix='')


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('path', type=str, help='Path to file or directory to upload. Like rsync, add a trailing slash '
                                               'to upload directory contents, no trailing slash to upload the '
                                               'directory itself.')
    parser.add_argument('api', type=str, help='HTTP REST API URL of a Tahoe-LAFS node')
    parser.add_argument('cap', type=str, help='Tahoe directory capability where files should be uploaded to')
    args = parser.parse_args()

    main(path_str=args.path, api=args.api, cap=args.cap)
