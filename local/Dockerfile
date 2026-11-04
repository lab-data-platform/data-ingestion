# A Lambda no runtime oficial da AWS (com o Runtime Interface Emulator), com o mesmo pacote do build/.
FROM public.ecr.aws/lambda/python:3.13
COPY build/package/ ${LAMBDA_TASK_ROOT}/
CMD ["labdata.sdk.runtime.lambda_handler.handler"]
