#!/usr/bin/env python

# This is a python script for container-native publishing of kubernetes job data for APEL accounting.
# It follows container-native practices such as using environment variables for configuration
# (likely from a ConfigMap), writing log info to stdout, etc.
# This script would likely run as an init container for a pod
# (wherein the main container would run ssmsend) launched as a CronJob.

# Requires python >= 3.6 for new f-strings

import argparse
import dateutil.relativedelta
import datetime
from dateutil.rrule import rrule, MONTHLY

from KAPELConfig import KAPELConfig
from prometheus_api_client import PrometheusConnect
from dirq.QueueSimple import QueueSimple
from timeit import default_timer as timer

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

def summaryMessage(config, year, month, wallDuration, cpuDuration, numJobs):
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
        f'WallDuration: {wallDuration}\n'
        f'CpuDuration: {cpuDuration}\n'
        f'NumberOfJobs: {numJobs}\n'
        f'Processors: {config.processors}\n'
        f'NodeCount: {config.nodecount}\n'
        f'%%\n'
    )
    return output

# return a list, each item of which is a dict representing a time period, in the form of
# an instant (end of the period) and a number of seconds to go back from then to reach the start of the period.
# Auto mode: there will be 2 dicts in the list, one for this month and one for last month.
# Gap mode: there will be a dict for each month in the gap period, and start and end are required.
def getTimePeriods(mode, startTime=None, endTime=None):
    if mode == 'auto':
        # get current time of script execution, in ISO8601 and UTC, ignoring microseconds.
        # This will be the singular reference time with respect to which we determine other times.
        runTime = datetime.datetime.now(tz=datetime.timezone.utc).replace(microsecond=0)
        startOfThisMonth = runTime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        startOfLastMonth = startOfThisMonth + dateutil.relativedelta.relativedelta(months=-1)
        return getGapTimePeriods(start=startOfLastMonth, end=runTime)
    elif mode == 'gap':
        return getGapTimePeriods(start=startTime, end=endTime)
    else:
        raise ValueError('Invalid mode')

def getGapTimePeriods(start, end):
    assert isinstance(start, datetime.datetime), "start is not type datetime.datetime"
    assert isinstance(end, datetime.datetime), "end is not type datetime.datetime"
    assert start < end, "start is not after end"

    # To avoid invalid dates (e.g. Feb 30) use the very beginning of the month to determine intervals
    intervalStart = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    assert intervalStart <= start
    # https://dateutil.readthedocs.io/en/stable/rrule.html
    intervals = list(rrule(freq=MONTHLY, dtstart=intervalStart, until=end))
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
            thisMonth = {
                'year': time.year,
                'month': time.month,
                'queryInstant': intervals[i + 1].isoformat(),
                'queryRangeSeconds': int((intervals[i + 1] - time).total_seconds())
            }
            periods.append(thisMonth)

    return periods

# Take a list of dicts from the prom query and construct a random-accessible dict
# (actually a list of tuples, so use dict() on the output) that can be referenced by the 'exported_pod' label as a key.
# Cast from string to float while we're at it.
# NB: this overwrites duplicate results if we get any from the prom query!
def rearrange(x):
    for item in x:
        yield item['metric']['exported_pod'], float(item['value'][1])

# process a time period (do prom query, process data, write output)
# takes a KAPELConfig object and one element of output from getTimePeriods
def processPeriod(config, iYear, iMonth, iInstant, iRange):

    print(f'Processing year {iYear}, month {iMonth}, starting at {iInstant} and going back {iRange}.')
    queries = QueryLogic(queryRange=iRange)

    # SSL generally not used for Prometheus access within a cluster
    # Docs on instant query API: https://prometheus.io/docs/prometheus/latest/querying/api/#instant-queries
    prom = PrometheusConnect(url=config.prometheus_server, disable_ssl=True)
    prom_connect_params = {'time': iInstant, 'timeout': config.query_timeout}

    rawResults, results, resultLengths = {}, {}, []
    # iterate over each query (cputime, starttime, endtime, cores) producing rawResults['cputime'] etc.
    for queryName, queryString in vars(queries).items():
        # Each of these rawResults is a list of dicts. Each dict in the list represents an individual data point, and contains:
        # 'metric': a dict of one or more key-value pairs of labels, one of which is the pod name ('exported_pod').
        # 'value': a list in which the 0th element is the timestamp of the value, and 1th element is the actual value we're interested in.
        print(f'Executing {queryName} query: {queryString}')
        rawResults[queryName] = prom.custom_query(query=queryString, params=prom_connect_params)
        results[queryName] = dict(rearrange(rawResults[queryName]))
        resultLengths.append(len(results[queryName]))
        print(f'Got {len(rawResults[queryName])} results from query, processed into {len(results[queryName])} items.')
        del rawResults[queryName]

    cputime = results['cputime']
    endtime = results['endtime']
    starttime = results['starttime']
    cores = results['cores']

    # Confirm the assumption that cputime (and endtime) should have the fewest entries, while starttime and cores may have additional ones
    # corresponding to jobs that have started but not finished yet. We only want the (completed) jobs for which all values are available.
    assert len(endtime) == min(resultLengths), "endtime should be the shortest list"

    summary_cputime, summary_walltime = 0, 0

    #code.interact(local=locals())

    start = timer()
    for key in endtime:
        # double check cputime calc of this job
        delta = abs(cputime[key] - (endtime[key] - starttime[key])*cores[key])
        assert delta < 0.001, "cputime calculation is inaccurate"
        # make sure walltime is positive
        walltime = endtime[key] - starttime[key]
        assert walltime > 0, "job end time is before start time"
        # sum up cputime and walltime over all jobs
        summary_cputime += cputime[key]
        summary_walltime += walltime

    summary_cputime = round(summary_cputime)
    summary_walltime = round(summary_walltime)

    print(f'total cputime: {summary_cputime}, total walltime: {summary_walltime}')
    # Write output to the message queue on local filesystem
    # https://dirq.readthedocs.io/en/latest/queuesimple.html#directory-structure
    dirq = QueueSimple(str(config.output_path))
    outputMessage = summaryMessage(config, year=iYear, month=iMonth, wallDuration=summary_walltime, cpuDuration=summary_cputime, numJobs=len(endtime))
    outFile = dirq.add(outputMessage)
    end = timer()
    print(f'Processed {len(endtime)} records in {end - start} s, writing output to {config.output_path}/{outFile}:')
    print('--------------------------------\n' + outputMessage + '--------------------------------')

def main(envFile):
    # TODO: need error handling if env file doesn't exist. See https://github.com/theskumar/python-dotenv/issues/297
    print('Starting KAPEL processor: ' + __file__)
    cfg = KAPELConfig(envFile)

    periods = getTimePeriods(cfg.publishing_mode, startTime=cfg.query_start, endTime=cfg.query_end)
    print('time periods:')
    print(periods)

    for i in periods:
        r = str(i['queryRangeSeconds']) + 's'
        processPeriod(config=cfg, iYear=i['year'], iMonth=i['month'], iInstant=i['queryInstant'], iRange=r)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Kubernetes job accounting data from Prometheus and prepare it for APEL publishing.")
    # This should be the only CLI argument, since all other config should be specified via env.
    parser.add_argument("-e", "--env-file", default=None, help="name of file containing environment variables for configuration")
    args = parser.parse_args()
    main(args.env_file)
