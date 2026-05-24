FROM nvcr.io/nvidia/tensorrt:26.04-py3

COPY common/install-asr-deps.sh /install-asr-deps.sh
RUN chmod +x /install-asr-deps.sh && /install-asr-deps.sh

COPY asr-init/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]