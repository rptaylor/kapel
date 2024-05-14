import sys
from datetime import datetime, timedelta
from dirq import QueueSimple
from random import randint

def summary_message(config, wall_time, cpu_time, start_time, end_time):
    output = (
        f'APEL-individual-job-message: v0.2\n'
        f'Site: {config.site_name}\n'
        f'VO: {config.vo_name}\n'
        f'MachineName: {config.machine_name}\n'
        f'LocalJobId: {randint(1000,10000)}\n'
        f'SubmitHost: {config.submit_host}\n'
        f'InfrastructureType: {config.infrastructure_type}\n'
        #f'InfrastructureDescription: {config.infrastructure_description}\n'
        # si2k = HS06 * 250
        f'ServiceLevelType: si2k\n'
        f'ServiceLevel: {config.benchmark_value * 250}\n'
        f'WallDuration: {wall_time}\n'
        f'CpuDuration: {cpu_time}\n'
        f'Processors: {config.processors}\n'
        f'NodeCount: {config.nodecount}\n'
        f'EndTime: {end_time}\n'
        f'StartTime: {start_time}\n'
        f'%%\n'
    )
    return output

class DummyConfig:
    def __init__(self, site_name, vo_name, submit_host, infrastructure_type='OSG', benchmark_value=1, processors=1, nodecount=1):
        self.site_name = site_name
        self.vo_name = vo_name
        self.submit_host = submit_host
        self.infrastructure_type = infrastructure_type
        self.benchmark_value = benchmark_value
        self.machine_name = "Sample Machine"
        self.processors = processors
        self.nodecount = nodecount


def main(output_dir, job_count, job_duration, site_name, vo_name, submit_host):
    end_time = datetime.now()
    start_time = end_time - timedelta(seconds=job_duration * job_count)
    config = DummyConfig(site_name, vo_name, submit_host)
    dirq = QueueSimple.QueueSimple(output_dir)
    for i in range(job_count):
        job_start = start_time + timedelta(seconds=i*job_duration)
        dirq.add(summary_message(
            config, 
            job_duration + randint(-5, 5), 
            job_duration + randint(-5, 5), 
            job_start.timestamp(),
            int(job_start.timestamp()) + randint(5, 20)))


if __name__ == '__main__':
    output_dir = sys.argv[1]
    job_count = int(sys.argv[2])
    job_duration = int(sys.argv[3])
    site_name = sys.argv[4]
    vo_name = sys.argv[5]
    submit_host = sys.argv[6]
    main(output_dir, job_count, job_duration, site_name, vo_name, submit_host)
