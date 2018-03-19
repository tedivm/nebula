FROM tiangolo/uwsgi-nginx-flask:python3.6

ADD requirements.txt /app/requirements.txt
RUN sed '/^uWSGI/ d' < /app/requirements.txt > /app/requirements_filtered.txt
WORKDIR /app/
RUN pip install -r requirements_filtered.txt

RUN /usr/bin/apt-get update; /usr/bin/apt-get install -f -y postgresql-client cron
ADD ./docker/app/crond /etc/cron.d/nebula

ENV STATIC_URL /app/nebula/static
ADD ./docker/app/uwsgi.ini /app/uwsgi.ini
ADD ./docker/app/prestart.sh /app/prestart.sh

ENV SETTINGS /app/SETTINGS

ADD ./db/ /app/db
ADD ./nebula/ /app/nebula
ADD ./bin/ /app/bin

RUN adduser --disabled-login --gecos '' nebula

RUN mkdir -p /home/nebula/.aws
RUN touch /home/nebula/.aws/credentials
RUN touch /home/nebula/.aws/config
RUN chown -R nebula:nebula /home/nebula/.aws
