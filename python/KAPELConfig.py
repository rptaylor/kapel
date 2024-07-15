# Configuration module for KAPEL

from environs import Env
from environs import EnvError

# Read config settings from environment variables (and a named env file in CWD if specified),
# do input validation, and return a config object. Note, if a '.env' file exists in CWD it will be used by default.
class KAPELConfig:
    def __init__(self, envFile=None):
        env = Env()
        # Read a .env file if one is specified, otherwise only environment variables will be used.
        env.read_env(envFile, recurse=False, verbose=True)

        # URL of the Prometheus server. Default value works within cluster for default bitnami/kube-prometheus Helm release.
        # Format: validity is determined by python urllib.parse.
        self.prometheus_server = env.url("PROMETHEUS_SERVER", "http://kube-prometheus-prometheus.kube-prometheus:9090").geturl()

        # Optionally add authentication headers - these are passed in under "Authorization"
        self.auth_header = env.str("PROMETHEUS_AUTH_HEADER", None)

        # The default behaviour ("auto" mode) is to publish records for the previous month, and up to the current day of the current month.
        self.publishing_mode = env.str("PUBLISHING_MODE", "auto")

        # The Kubernetes namespace to query. Only pods in this namespace will be accounted.
        self.namespace = env.str("NAMESPACE")

        self.summarize_records = env.bool("SUMMARIZE_RECORDS", True)

        # If PUBLISHING_MODE is "gap" instead, then a fixed time period will be queried instead and we need the start and end to be specified.
        # Format: ISO 8601, like "2020-12-20T07:20:50.52Z", to avoid complications with time zones and leap seconds.
        # Timezone should be specified, and it should be UTC for consistency with the auto mode publishing.
        # IMPORTANT NOTE: since only APEL summary records are supported (not individual job records),
        # if you specify QUERY_START as a time that is NOT precisely the beginning of a month, a partial month summary record will be produced and published.
        # The APEL server may ignore it if it already has a summary record for that month containing more jobs. Therefore when using gap mode make sure
        # that QUERY_START is precisely the beginning of a month in order to produce a complete summary record for that month which will take precedence over
        # any other records containing fewer jobs that may have already been published. The same applies for QUERY_END
        # matching the end of the month (unless it is the current month at the time of publishing, in which case a subsequent run in auto mode will eventually
        # complete the records for this month). So QUERY_START (and possibly QUERY_END) should look like e.g. '2021-02-01T00:00:00+00:00'
        if self.publishing_mode == "gap":
            self.query_start = env.datetime("QUERY_START")
            self.query_end = env.datetime("QUERY_END")
        else:
            # set a defined but invalid value to simplify time period functions
            self.query_start = None
            self.query_end = None

        # Timeout for the server to evaluate the query. Can take awhile for large-scale production use.
        # Format: https://prometheus.io/docs/prometheus/latest/querying/basics/#time-durations
        self.query_timeout = env.str("QUERY_TIMEOUT", "1800s")

        # Where to write the APEL message output.
        self.output_path = env.path("OUTPUT_PATH", "/srv/kapel")

        ## Info for APEL records, see https://wiki.egi.eu/wiki/APEL/MessageFormat
        # GOCDB site name
        self.site_name = env.str("SITE_NAME")

        # uniquely identifying name of cluster (like CE ID)  host_name:port/namespace
        self.submit_host = env.str("SUBMIT_HOST")

        # Benchmark type (HEPSPEC by default)
        #self.benchmark_type = env.str("BENCHMARK_TYPE", "HEPSPEC")

        # Benchmark value
        try:
            self.benchmark_value = env.float("BENCHMARK_VALUE")
        except EnvError:
            pass

        # VO of jobs
        self.vo_name = env.str("VO_NAME")

        # infrastructure info
        self.infrastructure_type = env.str("INFRASTRUCTURE_TYPE", "grid")

        # optionally define number of nodes and processors. Should not be necessary to
        # set a default of 0 here but see https://github.com/apel/apel/issues/241
        self.nodecount = env.int("NODECOUNT", 0)
        self.processors = env.int("PROCESSORS", 0)
