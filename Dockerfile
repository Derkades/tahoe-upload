FROM python:3.9-bullseye AS builder

RUN apt-get update

RUN pip install pyinstaller

RUN pip install tqdm requests

WORKDIR /data
COPY . .

RUN pyinstaller --name tahoe-upload upload.py

ENTRYPOINT ["bash", "/entrypoint.sh"]

FROM debian:bullseye-slim

COPY --from=builder /data/dist/tahoe-upload /tahoe-upload

ENTRYPOINT ["/tahoe-upload/tahoe-upload"]
