SQUEALY_BASE_DIR=squealy-home
FILES_TO_WATCH=$(find $SQUEALY_BASE_DIR -type f -name "*.yml" | tr '\n' ':' | rev | cut -c2- | rev)
pip install -r requirements.txt
SQUEALY_CONFIG_FILE=squealy-home/config.yml FLASK_APP=squealyapp FLASK_ENV=development flask run --extra-files=$FILES_TO_WATCH