#!/usr/bin/env python3

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
