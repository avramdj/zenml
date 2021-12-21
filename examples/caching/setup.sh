#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install tensorflow
}

pre_run_forced () {
  zenml integration install tensorflow -f
}