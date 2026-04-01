CONFIG ?= config/intel_v1.local.json
WINDOW_DAYS ?= 7
TOP_N ?= 12
REPORT_FILE ?= data/weekly_editorial_report_20260401.md
REDDIT_JSON ?=

.PHONY: dry-run collect pipeline weekly publish-weekly write-topics reddit-import

dry-run:
	python3 scripts/collect_intel_v1.py --config $(CONFIG) --dry-run

collect:
	python3 scripts/collect_intel_v1.py --config $(CONFIG) --write

pipeline:
	bash scripts/run_intel_pipeline.sh $(CONFIG)

weekly:
	python3 scripts/generate_weekly_topic_packet.py --config $(CONFIG) --days $(WINDOW_DAYS) --top-n $(TOP_N)

publish-weekly:
	python3 scripts/publish_weekly_report_to_base.py --config $(CONFIG) --report-file $(REPORT_FILE)

write-topics:
	python3 scripts/write_topics_from_editorial_report.py --config $(CONFIG) --report-file $(REPORT_FILE)

reddit-import:
	python3 scripts/ingest_reddit_export.py --config $(CONFIG) --input $(REDDIT_JSON) --write
