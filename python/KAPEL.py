#!/usr/bin/env python

# This is a python script for container-native publishing of kubernetes job data for APEL accounting.
# It follows container-native practices such as using environment variables for configuration
# (likely from a ConfigMap), writing log info to stdout, etc.
# This script would likely run as an init container for a pod
# (wherein the main container would run ssmsend) launched as a CronJob.

# Requires python >= 3.6 for new f-strings

import argparse
import datetime
from timeit import default_timer as timer
import dateutil.relativedelta
from dateutil.rrule import rrule, MONTHLY

from KAPELConfig import KAPELConfig
from prometheus_api_client import PrometheusConnect
from dirq.QueueSimple import QueueSimple

# for debugging
#import code
#from memory_profiler import profile

# Contains the PromQL queries
class QueryLogic:
    def __init__(self, queryRange):
        # Use a query that returns individual job records to get high granularity information, which can be processed into summary records as needed.

        # queryRange determines how far back to query. The query will cover the period from (t - queryRange) to t,
        # where 't' is defined in the Prometheus connection parameters.
        # See https://prometheus.io/docs/prometheus/latest/querying/basics/#range-vector-selectors
        # Format: https://prometheus.io/docs/prometheus/latest/querying/basics/#time-durations

        # Select the 'max_over_time' of each metric in the query range. The metrics we're looking at are constants that will not vary over time,
        # but selecting the max returns just one single point (instead of a list of multiple identical points) from each potentially non-aligned metric set.
        # On the CPU core side, some pods don't share all the same labels: pods that haven't yet gotten scheduled to a node don't have the node label,
        # so we filter out the rows where it's null with '{node != ""}'

        # Note: Prometheus renames some labels from KSM, e.g. from 'pod' to 'exported_pod', the latter of which is the label we're interested in.
        # The 'instance' and 'pod' labels in Prometheus actually represent the IP:port and name, respectively, of the KSM pod that Prometheus got the metric from.
        # When KSM is redeployed (or if the KSM deployment has > 1 pod), the 'instance' and 'pod' labels may have different values,
        # which would cause a label mismatch, so we use without to exclude them.
        # Also, use the 'max' aggregation operator (which only takes a scalar) on the result of max_over_time
        # (which takes a range and returns a scalar), and as a result get the whole metric set. Finally, use group_left for many-to-one matching.
        # https://prometheus.io/docs/prometheus/latest/querying/operators/#aggregation-operators
        # https://prometheus.io/docs/prometheus/latest/querying/operators/#many-to-one-and-one-to-many-vector-matches

        # Note some of these queries return duplicate results - without (instance, pod) does not seem to work properly.
        # Would be very bad but rearrange() overwrites duplicates
        self.cputime = f'(max_over_time(kube_pod_completion_time[{queryRange}]) - max_over_time(kube_pod_start_time[{queryRange}])) * on (exported_pod) group_left() max without (instance, pod) (max_over_time(kube_pod_container_resource_requests_cpu_cores{{node != ""}}[{queryRange}]))'
        self.endtime = f'max_over_time(kube_pod_completion_time[{queryRange}])'
        self.starttime = f'max_over_time(kube_pod_start_time[{queryRange}])'
        self.cores = f'max_over_time(kube_pod_container_resource_requests_cpu_cores{{node != ""}}[{queryRange}])'

def summary_message(config, year, month, wall_time, cpu_time, n_jobs, first_end, last_end):
    output = (
        f'APEL-summary-job-message: v0.2\n'
        f'Site: {config.site_name}\n'
        f'Month: {month}\n'
        f'Year: {year}\n'
        f'VO: {config.vo_name}\n'
        f'SubmitHost: {config.submit_host}\n'
        f'InfrastructureType: {config.infrastructure_type}\n'
        #f'InfrastructureDescription: {config.infrastructure_description}\n'
        # si2k = HS06 * 250
        f'ServiceLevelType: si2k\n'
        f'ServiceLevel: {config.benchmark_value * 250}\n'
        f'WallDuration: {wall_time}\n'
        f'CpuDuration: {cpu_time}\n'
        f'NumberOfJobs: {n_jobs}\n'
        f'Processors: {config.processors}\n'
        f'NodeCount: {config.nodecount}\n'
        f'EarliestEndTime: {first_end}\n'
        f'LatestEndTime: {last_end}\n'
        f'%%\n'
    )
    return output

def sync_message(config, year, month, n_jobs):
    output = (
        f'APEL-sync-message: v0.1\n'
        f'Site: {config.site_name}\n'
        f'SubmitHost: {config.submit_host}\n'
        f'NumberOfJobs: {n_jobs}\n'
        f'Month: {month}\n'
        f'Year: {year}\n'
        f'%%\n'
    )
    return output

# return a list, each item of which is a dict representing a time period, in the form of
# an instant (end of the period) and a number of seconds to go back from then to reach the start of the period.
# Auto mode: there will be 2 dicts in the list, one for this month so far and one for all of last month.
# Gap mode: there will be a dict for each month in the gap period, and start and end are required.
def get_time_periods(mode, start_time=None, end_time=None):
    if mode == 'auto':
        # get current time of script execution, in ISO8601 and UTC, ignoring microseconds.
        # This will be the singular reference time with respect to which we determine other times.
        run_time = datetime.datetime.now(tz=datetime.timezone.utc).replace(microsecond=0)
        start_of_this_month = run_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_last_month = start_of_this_month + dateutil.relativedelta.relativedelta(months=-1)
        return get_gap_time_periods(start=start_of_last_month, end=run_time)
    elif mode == 'gap':
        return get_gap_time_periods(start=start_time, end=end_time)
    else:
        raise ValueError('Invalid mode')

def get_gap_time_periods(start, end):
    assert isinstance(start, datetime.datetime), "start is not type datetime.datetime"
    assert isinstance(end, datetime.datetime), "end is not type datetime.datetime"
    assert start < end, "start is not after end"

    # To avoid invalid dates (e.g. Feb 30) use the very beginning of the month to determine intervals
    interval_start = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    assert interval_start <= start
    # https://dateutil.readthedocs.io/en/stable/rrule.html
    intervals = list(rrule(freq=MONTHLY, dtstart=interval_start, until=end))
    assert len(intervals) >= 1

    # Replace the 1st element of the list (which has day artificially set to 1) with the real start
    intervals.pop(0)
    intervals.insert(0, start)
    # make sure end is after the last interval, then add it as the last
    assert end > intervals[-1]
    intervals.append(end)
    assert len(intervals) >= 2
    # finally we have a list of intervals. Each item will be the start of a monthly publishing period, going until the next item.

    print('intervals:')
    for i in intervals:
        print(i.isoformat())

    periods = []
    for i, time in enumerate(intervals):
        # process all except the last item, since last one has already been used as the end for the previous item
        if i < len(intervals) - 1:
            periods.append({
                'year': time.year,
                'month': time.month,
                'instant': intervals[i + 1],
                'range_sec': int((intervals[i + 1] - time).total_seconds())
            })
    # return value is list of dicts of (int, int, datetime, int)
    return periods

# Take a list of dicts from the prom query and construct a random-accessible dict (casting from string to float while we're at it) via generator.
# (actually a list of tuples, so use dict() on the output) that can be referenced by the 'exported_pod' label as a key.
# NB: this overwrites duplicate results if we get any from the prom query!
def rearrange(x):
    for item in x:
        # this produces each of the (key, value) tuples in the list
        yield item['metric']['exported_pod'], float(item['value'][1])

# process a time period (do prom query, process data, write output)
# takes a KAPELConfig object and one element of output from get_time_periods
# Remember Prometheus queries go backwards: the time instant is the end, go backwards from there.
def process_period(config, period):
    period_start = period['instant'] + dateutil.relativedelta.relativedelta(seconds=-period['range_sec'])
    print(
        f"Processing year {period['year']}, month {period['month']}, "
        f"querying from {period['instant'].isoformat()} and going back {period['range_sec']} s to {period_start.isoformat()}."
    )
    queries = QueryLogic(queryRange=(str(period['range_sec']) + 's'))

    # SSL generally not used for Prometheus access within a cluster
    # Docs on instant query API: https://prometheus.io/docs/prometheus/latest/querying/api/#instant-queries
    prom = PrometheusConnect(url=config.prometheus_server, disable_ssl=True)
    prom_connect_params = {'time': period['instant'].isoformat(), 'timeout': config.query_timeout}

    raw_results, results, result_lengths = {}, {}, []
    # iterate over each query (cputime, starttime, endtime, cores) producing raw_results['cputime'] etc.
    for query_name, query_string in vars(queries).items():
        # Each of these raw_results is a list of dicts. Each dict in the list represents an individual data point, and contains:
        # 'metric': a dict of one or more key-value pairs of labels, one of which is the pod name ('exported_pod').
        # 'value': a list in which the 0th element is the timestamp of the value, and 1th element is the actual value we're interested in.
        print(f'Executing {query_name} query: {query_string}')
        t1 = timer()
        raw_results[query_name] = prom.custom_query(query=query_string, params=prom_connect_params)
        t2 = timer()
        results[query_name] = dict(rearrange(raw_results[query_name]))
        result_lengths.append(len(results[query_name]))
        t3 = timer()
        print(f'Query finished in {t2 - t1} s, processed in {t3 - t2} s. Got {len(results[query_name])} items from {len(raw_results[query_name])} results.')
        del raw_results[query_name]

    cputime = results['cputime']
    endtime = results['endtime']
    starttime = results['starttime']
    cores = results['cores']

    # Confirm the assumption that cputime (and endtime) should have the fewest entries, while starttime and cores may have additional ones
    # corresponding to jobs that have started but not finished yet. We only want the (completed) jobs for which all values are available.
    # Note that jobs which started last month and finished this month will be properly included and accounted in this month.
    assert len(endtime) == min(result_lengths), "endtime should be the shortest list"

    # However, jobs that finished last month may show up in this month's data if they are still present on the cluster this month (in Completed state).
    # Exclude them by filtering with a lambda (since you can't pass an argument to a function object AFAIK).
    endtime = dict(filter(lambda x: x[1] >= datetime.datetime.timestamp(period_start), endtime.items()))

    # avoid sending empty records
    if len(endtime) == 0:
        print('No records to process.')
        return

    sum_cputime = 0
    t4 = timer()
    for key in endtime:
        assert endtime[key] > starttime[key], "job end time is before start time"
        # double check cputime calc of this job
        delta = abs(cputime[key] - (endtime[key] - starttime[key])*cores[key])
        assert delta < 0.001, "cputime calculation is inaccurate"
        sum_cputime += cputime[key]

    # CPU time as calculated here means (# cores * job duration), which apparently corresponds to
    # the concept of wall time in APEL accounting. It is not clear what CPU time means in APEL;
    # could be the actual CPU usage % integrated over the job (# cores * job duration * usage)
    # but this does not seem to be documented clearly. Some batch systems do not actually measure
    # this so it is not reported consistently or accurately. Some sites have CPU efficiency
    # (presumably defined as CPU time / wall time) time that is up to ~ 500% of the walltime, or
    # always fixed at 100%. In Kubernetes, the actual CPU usage % is tracked by metrics server
    # (not KSM), which is not meant to be used for monitoring or accounting purposes and is not
    # scraped by Prometheus. So just use walltime = cputime
    sum_cputime = round(sum_cputime)
    sum_walltime = sum_cputime

    print(f'total cputime: {sum_cputime}, total walltime: {sum_walltime}')
    # Write output to the message queue on local filesystem
    # https://dirq.readthedocs.io/en/latest/queuesimple.html#directory-structure
    dirq = QueueSimple(str(config.output_path))
    summary_output = summary_message(
        config,
        year=period['year'],
        month=period['month'],
        wall_time=sum_walltime,
        cpu_time=sum_cputime,
        n_jobs=len(endtime),
        # this appears faster than getting min/max during the dict iteration above
        first_end=round(min(endtime.values())),
        last_end=round(max(endtime.values()))
    )
    sync_output = sync_message(config, year=period['year'], month=period['month'], n_jobs=len(endtime))
    t5 = timer()
    summary_file = dirq.add(summary_output)
    sync_file = dirq.add(sync_output)
    print(f'Analyzed {len(endtime)} records in {t5 - t4} s.')
    print(f'Writing summary record to {config.output_path}/{summary_file}:')
    print('--------------------------------\n' + summary_output + '--------------------------------')
    print(f'Writing sync record to {config.output_path}/{sync_file}:')
    print('--------------------------------\n' + sync_output + '--------------------------------')

def main(envFile):
    # TODO: need error handling if env file doesn't exist. See https://github.com/theskumar/python-dotenv/issues/297
    print('Starting KAPEL processor: ' + __file__)
    cfg = KAPELConfig(envFile)

    periods = get_time_periods(cfg.publishing_mode, start_time=cfg.query_start, end_time=cfg.query_end)
    print('time periods:')
    print(periods)

    for p in periods:
        process_period(config=cfg, period=p)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Kubernetes job accounting data from Prometheus and prepare it for APEL publishing.")
    # This should be the only CLI argument, since all other config should be specified via env.
    parser.add_argument("-e", "--env-file", default=None, help="name of file containing environment variables for configuration")
    args = parser.parse_args()
    main(args.env_file)
