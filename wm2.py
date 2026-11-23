import ftputil

with ftputil.FTPHost(
    "ftpmirror.your.org", user="anonymous", passwd="", encoding="utf-8"
) as ft:
    ft.chdir("/pub/wikimedia/dumps/other/mediawiki_content_history")
