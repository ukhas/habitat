#!/bin/bash
/usr/bin/pandoc -s -r html overview.html -o overview.md
/usr/bin/pandoc -s -r html jobs.html -o jobs.md
