import os
import chardet
import argparse
import subprocess
import shutil
import sys

def find_lyrics(song_name, lyrics_files):
    """ 根据歌曲文件名找到匹配的 LRC 歌词文件 """
    base_name = os.path.splitext(song_name)[0]
    for lyrics_file in lyrics_files:
        if lyrics_file.startswith(base_name):
            return lyrics_file
    return None

def find_lyrics_in_dir(song_name, lyrics_dir):
    """ 在指定目录中查找匹配的歌词文件 """
    base_name = os.path.splitext(song_name)[0]
    
    # 如果目录不存在，直接返回None
    if not os.path.isdir(lyrics_dir):
        return None
        
    # 获取歌词目录下所有lrc文件
    lrc_files = [f for f in os.listdir(lyrics_dir) if f.lower().endswith('.lrc')]
    
    # 查找匹配的歌词文件
    for lrc_file in lrc_files:
        if lrc_file.startswith(base_name):
            return os.path.join(lyrics_dir, lrc_file)
    
    return None

def find_cover_in_dir(song_name, cover_dir):
    """ 在指定目录中查找匹配的封面图片 """
    if not cover_dir or not os.path.isdir(cover_dir):
        return None
        
    base_name = os.path.splitext(song_name)[0]
    
    # 支持的图片格式
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
    
    # 获取封面目录下所有图片文件
    cover_files = [f for f in os.listdir(cover_dir) if f.lower().endswith(image_extensions)]
    
    # 查找匹配的封面文件
    for cover_file in cover_files:
        file_base = os.path.splitext(cover_file)[0]
        if file_base == base_name or base_name.startswith(file_base) or file_base.startswith(base_name):
            return os.path.join(cover_dir, cover_file)
    
    return None

def detect_encoding(file_path):
    """ 使用 chardet 自动检测 LRC 文件的编码 """
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']

def read_lrc_file(lyrics_file, lyrics_encoding):
    """ 读取 LRC 歌词，使用指定编码解析，并忽略非法字符 """
    try:
        with open(lyrics_file, 'r', encoding=lyrics_encoding, errors='ignore') as f:
            lyrics = f.read().lstrip('\ufeff')  # 去掉 UTF-8 BOM 头
        return lyrics
    except Exception as e:
        print(f"❌ 读取 {lyrics_file} 失败: {e}")
        # 尝试使用自动检测的编码
        try:
            detected_encoding = detect_encoding(lyrics_file)
            print(f"🔍 尝试使用自动检测的编码: {detected_encoding}")
            with open(lyrics_file, 'r', encoding=detected_encoding, errors='ignore') as f:
                lyrics = f.read().lstrip('\ufeff')
            return lyrics
        except Exception as e2:
            print(f"❌ 再次尝试读取 {lyrics_file} 失败: {e2}")
            return None

def check_gpu_support():
    """检查是否支持NVIDIA GPU加速"""
    try:
        # 检查ffmpeg是否支持NVENC
        result = subprocess.run(
            ['ffmpeg', '-encoders'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 检查输出中是否包含nvenc
        return 'nvenc' in result.stdout.lower()
    except Exception:
        return False

def embed_lyrics_mp3(audio_file, lyrics_text, temp_lrc_path, cover_file=None, use_gpu=False, skip_lyrics=False):
    """ 使用 ffmpeg 将歌词嵌入 MP3 文件 """
    try:
        # 如果没有歌词也没有封面，直接返回
        if skip_lyrics and not cover_file:
            print(f"⚠️ 跳过处理: {os.path.basename(audio_file)} - 没有指定歌词和封面")
            return False
            
        # 如果有歌词，先将歌词内容写入临时文件
        if not skip_lyrics:
            with open(temp_lrc_path, 'w', encoding='utf-8') as f:
                f.write(lyrics_text)
        
        # 构建输出文件名，保持相同的扩展名
        file_ext = os.path.splitext(audio_file)[1]
        output_file = os.path.splitext(audio_file)[0] + ".temp" + file_ext
        
        # 基本命令参数
        cmd = ['ffmpeg', '-y']
        
        # 添加音频输入
        cmd.extend(['-i', audio_file])
        
        # 添加歌词输入(如果需要嵌入歌词)
        if not skip_lyrics:
            cmd.extend(['-i', temp_lrc_path])
        
        # 添加封面图片输入（如果有）
        if cover_file and os.path.exists(cover_file):
            cmd.extend(['-i', cover_file])
        
        # 配置映射和编码参数
        if not skip_lyrics and cover_file and os.path.exists(cover_file):
            # 有歌词和封面
            if use_gpu and check_gpu_support():
                cmd.extend([
                    '-map', '0:a',      # 音频流
                    '-map', '1',        # 歌词流
                    '-map', '2',        # 封面流
                    '-c:a', 'copy',     # 复制音频
                    '-c:s', 'copy',     # 复制字幕
                    '-disposition:1', 'lyrics',
                    '-disposition:2', 'attached_pic'
                ])
            else:
                cmd.extend([
                    '-map', '0:a',      # 音频流
                    '-map', '1',        # 歌词流
                    '-map', '2',        # 封面流
                    '-c', 'copy',       # 复制所有流
                    '-disposition:1', 'lyrics',
                    '-disposition:2', 'attached_pic'
                ])
        elif not skip_lyrics:
            # 只有歌词，没有封面
            if use_gpu and check_gpu_support():
                cmd.extend([
                    '-map', '0:a',     # 音频流
                    '-map', '1',       # 歌词流
                    '-c:a', 'copy',    # 复制音频
                    '-c:s', 'copy',    # 复制字幕
                    '-disposition:1', 'lyrics'
                ])
            else:
                cmd.extend([
                    '-map', '0',       # 音频流
                    '-map', '1',       # 歌词流
                    '-c', 'copy',      # 复制所有流
                    '-disposition:1', 'lyrics'
                ])
        elif cover_file and os.path.exists(cover_file):
            # 只有封面，没有歌词
            if use_gpu and check_gpu_support():
                cmd.extend([
                    '-map', '0:a',     # 音频流
                    '-map', '1',       # 封面流
                    '-c:a', 'copy',    # 复制音频
                    '-c:v', 'copy',    # 复制视频
                    '-disposition:1', 'attached_pic'
                ])
            else:
                cmd.extend([
                    '-map', '0',       # 音频流
                    '-map', '1',       # 封面流
                    '-c', 'copy',      # 复制所有流
                    '-disposition:1', 'attached_pic'
                ])
            
        # 添加输出文件和日志级别
        cmd.extend(['-loglevel', 'quiet', output_file])
        
        # 执行ffmpeg命令，不显示输出
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                text=True, encoding='utf-8', errors='replace')
        
        # 检查ffmpeg是否成功执行
        if process.returncode != 0:
            print(f"❌ 处理MP3失败: {os.path.basename(audio_file)}")
            return False
            
        # 检查输出文件是否存在
        if not os.path.exists(output_file):
            print(f"❌ 未能创建输出文件: {os.path.basename(output_file)}")
            return False
        
        # 替换原文件
        os.remove(audio_file)
        os.rename(output_file, audio_file)
        
        # 删除临时歌词文件
        if not skip_lyrics and os.path.exists(temp_lrc_path):
            os.remove(temp_lrc_path)
        
        return True
    except FileNotFoundError:
        print("❌ 未找到ffmpeg程序，请确保ffmpeg已安装并添加到系统路径中")
        return False
    except Exception as e:
        print(f"❌ 处理 {os.path.basename(audio_file)} 失败: {e}")
        if not skip_lyrics and os.path.exists(temp_lrc_path):
            os.remove(temp_lrc_path)
        return False

def embed_lyrics_flac(audio_file, lyrics_text, temp_lrc_path, cover_file=None, use_gpu=False, skip_lyrics=False):
    """ 使用 ffmpeg 将歌词嵌入 FLAC 文件 """
    try:
        # 如果没有歌词也没有封面，直接返回
        if skip_lyrics and not cover_file:
            print(f"⚠️ 跳过处理: {os.path.basename(audio_file)} - 没有指定歌词和封面")
            return False
        
        # 如果有歌词，先将歌词内容写入临时文件
        if not skip_lyrics:
            with open(temp_lrc_path, 'w', encoding='utf-8') as f:
                f.write(lyrics_text)
        
        # 创建临时目录
        temp_dir = os.path.join(os.path.dirname(audio_file), "temp_lyrics_dir")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 构建输出文件路径
        output_file = os.path.join(temp_dir, os.path.basename(audio_file))
        
        # 基本命令参数
        cmd = ['ffmpeg', '-y']
        
        # 添加音频输入
        cmd.extend(['-i', audio_file])
        
        # 如果有封面，添加封面输入
        cover_index = 1  # 封面流索引
        if skip_lyrics:
            cover_index = 1  # 无歌词时，封面是第1个额外流
        else:
            cover_index = 1  # 有歌词但在FLAC中不作为单独流，封面是第1个额外流
            
        cover_option = []
        if cover_file and os.path.exists(cover_file):
            cmd.extend(['-i', cover_file])
            cover_option = ['-metadata:s:v', 'title="Album cover"', 
                          '-metadata:s:v', 'comment="Cover (front)"']
        
        # 添加编码参数
        cmd.extend(['-c', 'copy'])
        
        # 添加元数据参数
        if not skip_lyrics:
            cmd.extend(['-metadata', f'lyrics={lyrics_text}'])
            
        # 添加封面处理参数（如果有封面）
        if cover_file and os.path.exists(cover_file):
            cmd.extend(cover_option)
            
        # 添加输出文件和日志级别
        cmd.extend(['-loglevel', 'quiet', output_file])
        
        # 静默执行ffmpeg命令
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                             text=True, encoding='utf-8', errors='replace')
        
        if process.returncode != 0:
            print(f"❌ 处理FLAC失败: {os.path.basename(audio_file)}")
            return False
            
        # 检查输出文件是否存在
        if not os.path.exists(output_file):
            print(f"❌ 未能创建输出文件: {os.path.basename(output_file)}")
            return False
        
        # 替换原文件
        shutil.move(output_file, audio_file)
        
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        
        return True
    except Exception as e:
        print(f"❌ 处理 {os.path.basename(audio_file)} 失败: {e}")
        return False
    finally:
        # 删除临时歌词文件
        if not skip_lyrics and os.path.exists(temp_lrc_path):
            os.remove(temp_lrc_path)

def main(song_dir, lyrics_dir, cover_dir, lyrics_encoding, keep_lyrics, use_gpu, skip_lyrics):
    """ 主函数，遍历目录并嵌入歌词 """
    if not os.path.isdir(song_dir):
        print("❌ 目录路径无效，请检查路径是否正确。")
        return
        
    # 检查是否至少有一项要嵌入
    if skip_lyrics and not cover_dir:
        print("❌ 错误：必须至少指定一项要嵌入的内容（歌词或封面）。")
        return

    # 检查ffmpeg是否可用
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                      encoding='utf-8', errors='replace')
    except FileNotFoundError:
        print("❌ 未找到ffmpeg程序，请确保ffmpeg已安装并添加到系统路径中")
        return

    # 如果要使用GPU，检查是否支持
    if use_gpu:
        if check_gpu_support():
            print("🔍 启用NVIDIA GPU加速")
        else:
            print("⚠️ 系统不支持NVIDIA GPU加速，将使用CPU模式")
            use_gpu = False

    # 获取目录下的所有文件
    files = os.listdir(song_dir)
    
    # 获取音频文件和歌词文件 - 排除临时文件
    audio_files = [f for f in files if f.lower().endswith(('.mp3', '.flac')) and '.temp.' not in f]
    
    # 如果需要嵌入歌词，则检查歌词目录
    lrc_files = []
    if not skip_lyrics:
        if lyrics_dir is None or lyrics_dir == song_dir:
            lrc_files = [f for f in files if f.lower().endswith('.lrc')]
            lyrics_dir = song_dir
            print(f"🔍 从歌曲目录读取歌词文件")
        else:
            if os.path.isdir(lyrics_dir):
                lrc_files = [f for f in os.listdir(lyrics_dir) if f.lower().endswith('.lrc')]
                print(f"🔍 从指定歌词目录读取歌词文件: {lyrics_dir}")
            else:
                print(f"⚠️ 指定的歌词目录不存在，将使用歌曲目录: {song_dir}")
                lrc_files = [f for f in files if f.lower().endswith('.lrc')]
                lyrics_dir = song_dir
    else:
        print("🔍 跳过歌词嵌入")
    
    # 检查封面目录
    has_cover = False
    if cover_dir and os.path.isdir(cover_dir):
        has_cover = True
        print(f"🔍 从指定目录读取封面图片: {cover_dir}")
    elif cover_dir:
        print(f"⚠️ 指定的封面目录不存在: {cover_dir}")

    if not audio_files:
        print("❌ 没有找到 MP3 或 FLAC 文件！")
        return

    if not skip_lyrics:
        print(f"🔍 使用编码: {lyrics_encoding} 处理歌词文件")
        print(f"🔍 {'保留' if keep_lyrics else '删除'}歌词文件")
    
    processed_count = 0
    for audio in audio_files:
        # 先在歌词目录中查找
        full_lrc_path = None
        lrc_file = None
        lyrics_text = None
        
        # 如果不跳过歌词嵌入，则查找歌词文件
        if not skip_lyrics:
            if lyrics_dir != song_dir:
                # 在指定的歌词目录中查找
                full_lrc_path = find_lyrics_in_dir(audio, lyrics_dir)
                if full_lrc_path:
                    lrc_file = os.path.basename(full_lrc_path)
            else:
                # 在歌曲目录中查找
                lrc_file = find_lyrics(audio, lrc_files)
                if lrc_file:
                    full_lrc_path = os.path.join(song_dir, lrc_file)
            
            # 如果找到歌词文件，读取内容
            if full_lrc_path and os.path.exists(full_lrc_path):
                lyrics_text = read_lrc_file(full_lrc_path, lyrics_encoding)
                if not lyrics_text:
                    print(f"⚠️ 无法读取 {audio} 对应的歌词文件内容")
                    if not has_cover:
                        continue  # 如果没有封面，则跳过此文件
            elif not has_cover:
                print(f"⚠️ 未找到 {audio} 对应的歌词文件")
                continue  # 如果没有封面，则跳过此文件
        
        # 查找封面文件
        cover_file = None
        if has_cover:
            cover_file = find_cover_in_dir(audio, cover_dir)
            if not cover_file and skip_lyrics:
                print(f"⚠️ 未找到 {audio} 对应的封面文件")
                continue  # 如果跳过歌词且没有找到封面，则跳过此文件
        
        # 如果既没有歌词也没有封面，跳过处理
        if (skip_lyrics or not lyrics_text) and not cover_file:
            print(f"⚠️ 跳过处理 {audio}: 没有歌词和封面可嵌入")
            continue
            
        temp_lrc_path = os.path.join(song_dir, f"temp_{os.getpid()}.lrc") if not skip_lyrics else None
        audio_path = os.path.join(song_dir, audio)
        
        # 根据音频文件类型选择不同的嵌入方法
        success = False
        if audio.lower().endswith('.mp3'):
            success = embed_lyrics_mp3(audio_path, lyrics_text, temp_lrc_path, cover_file, use_gpu, skip_lyrics)
        elif audio.lower().endswith('.flac'):
            success = embed_lyrics_flac(audio_path, lyrics_text, temp_lrc_path, cover_file, use_gpu, skip_lyrics)
        
        # 根据参数和处理结果决定是否删除原歌词文件
        if success:
            processed_count += 1
            # 构建成功信息
            lyrics_msg = "" if skip_lyrics else "歌词"
            cover_msg = "" if not cover_file else "封面"
            both_msg = "和" if not skip_lyrics and cover_file else ""
            
            if not skip_lyrics and not keep_lyrics and lyrics_dir == song_dir and full_lrc_path:
                try:
                    os.remove(full_lrc_path)
                    print(f"✅ 已嵌入{lyrics_msg}{both_msg}{cover_msg}并删除原歌词文件: {audio}")
                except Exception as e:
                    print(f"✅ 已嵌入{lyrics_msg}{both_msg}{cover_msg}但无法删除原歌词文件: {audio}")
            else:
                print(f"✅ 已嵌入{lyrics_msg}{both_msg}{cover_msg}: {audio}")
    
    print(f"✅ 共处理 {processed_count}/{len(audio_files)} 个文件")

if __name__ == "__main__":
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='将LRC歌词嵌入到音频文件中')
    parser.add_argument('--dir', '-d', type=str, default=r"D:\临时\歌曲下载\酷我",
                        help='歌曲文件所在的目录路径')
    parser.add_argument('--lyrics-dir', '-l', type=str, default=None,
                        help='歌词文件所在的目录路径，默认与歌曲目录相同')
    parser.add_argument('--cover-dir', '-c', type=str, default=None,
                        help='封面图片所在的目录路径，如不指定则不添加封面')
    parser.add_argument('--encoding', '-e', type=str, default='gb2312',
                        help='歌词文件的编码，默认为gb2312，可选utf-8等')
    parser.add_argument('--keep-lyrics', '-k', action='store_true',
                        help='嵌入歌词后是否保留原歌词文件，默认删除')
    parser.add_argument('--use-gpu', '-g', action='store_true',
                        help='是否使用NVIDIA GPU加速处理，需要ffmpeg支持NVENC')
    parser.add_argument('--skip-lyrics', '-s', action='store_true',
                        help='是否跳过嵌入歌词，只嵌入封面')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 检查是否至少有一项嵌入内容
    if args.skip_lyrics and not args.cover_dir:
        print("❌ 错误：必须至少指定一项要嵌入的内容（歌词或封面）。")
        sys.exit(1)
    
    # 调用主函数
    main(args.dir, args.lyrics_dir, args.cover_dir, args.encoding, args.keep_lyrics, args.use_gpu, args.skip_lyrics)
    
    print("处理完成，按任意键退出...")
    input()
