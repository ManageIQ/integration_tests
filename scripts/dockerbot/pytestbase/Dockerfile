FROM cfmeqe/dockerbot-checkouts
ADD setup.sh /setup.sh
ADD post_result.py /post_result.py
ADD get_keys.py /get_keys.py
ADD verify_commit.py /verify_commit.py
RUN mkdir /log_depot

VOLUME ["/log_depot"]
WORKDIR /integration_tests
ENTRYPOINT ["bash", "/setup.sh"]