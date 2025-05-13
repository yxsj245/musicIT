# musicIT
一个音乐歌曲快速嵌入歌词以及封面的脚本，基于ffmpeg

# 如何使用
## 安装FFmpeg 并设置环境变量
[https://blog.csdn.net/m0_47449768/article/details/130102406](https://blog.csdn.net/m0_47449768/article/details/130102406)
## 下载程序
从左侧发行版中下载最新二进制编译可执行文件，放入任意目录下，在此目录下创建`run.bat`脚本，参数如下
```bat
musicIT.exe --dir "D:\临时\歌曲下载\酷我" --encoding gb2312
```
可替换填写参数 \
`--encoding gb2312` 歌词文件编码，可通过编辑器中获取
```bat
# 默认操作 - 嵌入歌词
musicIT.exe

# 指定目录嵌入歌词
-d "D:\我的音乐"

# 嵌入歌词和封面，保留原歌词文件
-d "D:\音乐" -c "D:\封面" -k

# 只嵌入封面不嵌入歌词
-d "D:\音乐" -c "D:\封面" -s

# 使用UTF-8编码的歌词文件，启用GPU加速
-d "D:\音乐" -e utf-8 -g
```
