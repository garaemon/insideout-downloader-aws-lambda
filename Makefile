FFMPEG_URL=https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
ZIP_FILE=insideout_downloader.zip
# INSIDEOUT_S3_BUCKET=
INSIDEOUT_S3_KEY=${ZIP_FILE}

all: ${ZIP_FILE}

${ZIP_FILE}: ffmpeg lambda_function.py skicka skicka.config requirements.txt skicka.tokencache.json ytmusic_headers_auth.json
	rm -f $@
	(virtualenv .venv && . .venv/bin/activate && pip install --target ./package -r requirements.txt)
	(cd package && zip -r9 ../$@ . --exclude=*.git* --exclude=*.pyc)
	zip -g $@ $^
	rm -rf ./package

ffmpeg:
	wget ${FFMPEG_URL} -O /tmp/ffmpeg.tar.xz
	(cd /tmp && tar xvf /tmp/ffmpeg.tar.xz)
	cp /tmp/ffmpeg-4.2.2-amd64-static/ffmpeg .


skicka:
	GOPATH=${PWD}/tmp GOARCH=amd64 GOOS=linux go get github.com/google/skicka
	cp tmp/bin/linux_amd64/skicka .

deploy: ${ZIP_FILE}
	make s3
	aws lambda update-function-code --s3-bucket ${INSIDEOUT_S3_BUCKET} --s3-key ${INSIDEOUT_S3_KEY} --function-name insideout

s3: ${ZIP_FILE}
	aws s3 cp $< s3://${INSIDEOUT_S3_BUCKET}/$<
