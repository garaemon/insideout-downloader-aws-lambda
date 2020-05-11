import logging
import os
import glob
from google_music_manager_uploader.uploader_daemon import (
    Musicmanager, MusicToUpload, DeduplicateApi, Observer, upload_file)


# Re-define google_music_manager_uploader.uploader_daemon.upload not to call sys.exit
def upload(
    directory: str = '.',
    oauth: str = os.environ['HOME'] + '/oauth',
    remove: bool = False,
    uploader_id: str = '',
    oneshot: bool = False,
    deduplicate_api: str = None,
) -> None:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.info("Init Daemon - Press Ctrl+C to quit")

    api = Musicmanager()
    if not api.login(oauth, uploader_id):
        raise ValueError("Error with oauth credentials")
    observer = None
    deduplicate = DeduplicateApi(deduplicate_api) if deduplicate_api else None
    if not oneshot:
        event_handler = MusicToUpload()
        event_handler.api = api
        event_handler.oauth = oauth
        event_handler.uploader_id = uploader_id
        event_handler.path = directory
        event_handler.remove = remove
        event_handler.logger = logger
        event_handler.deduplicate_api = deduplicate
        observer = Observer()
        observer.schedule(event_handler, directory, recursive=True)
        observer.start()
    files = [file for file in glob.glob(glob.escape(directory) + '/**/*', recursive=True)]
    for file_path in files:
        upload_file(api, file_path, logger, remove=remove, deduplicate_api=deduplicate)
    if oneshot:
        return
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
