FROM python:3.12

COPY pyproject.toml README.md /app/
COPY src/ /app/src 
WORKDIR /app 
RUN pip install . 

ENV PORT=32453
ENV NBQUIZ_TESTBANKS=/testbank/testbank.zip
CMD nbquiz server 
