#!/usr/bin/env bash

ENV_NAME="sg-translations"
YML_FILE="environment.yml"
PIP_FILE="environment.txt"

RUN_SCRIPT="run.sh"
FUNCTION_NAME="translations"
JHA_HOME_NAME="JHA_HOME"

BASEDIR=$(cd "$(dirname "$0")/"; pwd)

if [ -x "$(command -v conda)" ]; then
    conda env create --name $ENV_NAME --file $YML_FILE --force
  else
  	echo "WARNING: Conda not available, falling back to pip"
  	echo "Some python packages need to be installed. These might overwrite your existing base environment packages and can cause trouble."

  	read -p "Do you want to continue without conda (y/[n])? " -n 1 -r
	echo
	if [[ $REPLY =~ ^[Yy]$ ]]
	then
		pip install -r $PIP_FILE
	else
		exit
	fi
fi

echo "function $FUNCTION_NAME { $BASEDIR/$RUN_SCRIPT \$1; }" >> ~/.bash_profile

DEFAULT_JHA_HOME=~
eval DEFAULT_JHA_HOME="$DEFAULT_JHA_HOME/taloom/just-hire-angular"

echo "Please provide the path to your Just Hire Angular directory. It will be saved to \$$JHA_HOME_NAME."
read -p "\$$JHA_HOME_NAME [$DEFAULT_JHA_HOME]: " JHA_HOME
JHA_HOME=${JHA_HOME:-$DEFAULT_JHA_HOME}
echo "export $JHA_HOME_NAME=$JHA_HOME" >> ~/.bash_profile

clear