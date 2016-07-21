.PHONY: metadata
metadata:
	@echo "Updating extra-info metadata for bundle"
	@charm set cs:~bigdata-charmers/bundle/realtime-syslog-analytics conjure-up:='{"friendly-name": "Realtime Syslog Analytics", "version": 1}'

all: metadata
