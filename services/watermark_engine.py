"""原生水印绘制及与原网页 RWM2 格式兼容的像素水印。"""
import math
import struct
from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QImageReader,QPainter,QPainterPath,QFont,QFontMetricsF,QColor,QPen

DEFAULTS=dict(text='Rinull_xiaomai',fill='#ffffff',stroke_color='#111111',mode='单个',position=8,size=6,opacity=38,angle=-18,margin=4,spacing=18,weight=700,stroke=.04,shadow=True,protect=True,hidden=True,hidden_text='Rinull_xiaomai 版权所有',key='',format='PNG')

def fnv(data):
    value=2166136261
    for byte in data: value=((value^byte)*16777619)&0xffffffff
    return value

def hash_text(text): return fnv(text.encode('utf-8'))

def xor(data,key):
    value=hash_text('encrypt|'+key) or 1; result=bytearray()
    for byte in data:
        value^=(value<<13)&0xffffffff;value^=value>>17;value^=(value<<5)&0xffffffff;value&=0xffffffff
        result.append(byte^(value&255))
    return bytes(result)

def pixel_map(width,height,key):
    capacity=width*height
    if capacity<96: raise ValueError('图片太小，无法容纳隐形水印。')
    step=(hash_text(f'{key}|{width}x{height}|rinull-watermark')%(capacity-1))|1
    while math.gcd(step,capacity)!=1:step+=2
    return capacity,step,hash_text(key+'|offset')%capacity

def embed(image,text,key):
    if not key:raise ValueError('隐形水印密钥不能为空。')
    if not text.strip():raise ValueError('隐形水印内容不能为空。')
    data=text.strip().encode('utf-8'); payload=b'RWM2'+struct.pack('>II',len(data),fnv(data))+xor(data,key)
    image=image.convert('RGBA');w,h=image.size;capacity,step,offset=pixel_map(w,h,key)
    if len(payload)*8>capacity:raise ValueError(f'图片容量不足，隐形内容最多支持 {max(0,capacity//8-12)} 字节。')
    raw=bytearray(image.tobytes())
    for i in range(len(payload)*8):
        channel=((offset+i*step)%capacity)*4+2
        raw[channel]=(raw[channel]&254)|((payload[i//8]>>(7-i%8))&1)
    return Image.frombytes('RGBA',image.size,bytes(raw))

def read_hidden(image,key):
    if not key:raise ValueError('请输入用于验证的密钥。')
    image=image.convert('RGBA');w,h=image.size;capacity,step,offset=pixel_map(w,h,key);raw=image.tobytes()
    def read(count,start=0):
        data=bytearray(count)
        for i in range(count*8):data[i//8]|=(raw[((offset+(start+i)*step)%capacity)*4+2]&1)<<(7-i%8)
        return bytes(data)
    header=read(12)
    if header[:4]!=b'RWM2':raise ValueError('未检测到隐形水印：可能密钥不匹配，或图片已被压缩、缩放。')
    length,checksum=struct.unpack('>II',header[4:])
    if not 0<length<=capacity//8-12:raise ValueError('水印长度异常，可能密钥错误或图片已损坏。')
    plain=xor(read(length,96),key)
    if fnv(plain)!=checksum:raise ValueError('密钥不匹配，或隐形水印已被破坏。')
    return plain.decode('utf-8')

def render(ctx,source,settings,preview=False):
    reader=QImageReader(str(source));reader.setAutoTransform(True)
    if preview:
        size=reader.size()
        if size.isValid() and max(size.width(),size.height())>1200:
            reader.setScaledSize(size.scaled(1200,1200,Qt.AspectRatioMode.KeepAspectRatio))
    image=reader.read()
    if image.isNull():raise ValueError('图片无法读取，请选择有效的 PNG、JPG 或 WEBP 图片。')
    image=image.convertToFormat(QImage.Format.Format_ARGB32);w,h=image.width(),image.height();base=min(w,h)
    lines=[s.strip() for s in settings['text'].splitlines() if s.strip()]
    painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    try:
        def layer(size,opacity,angle,spacing,stroke,shadow,tile):
            font=QFont('Microsoft YaHei UI');font.setPixelSize(size);font.setWeight(QFont.Weight(settings['weight']))
            metrics=QFontMetricsF(font);line_h=round(size*1.25);bw=max(metrics.horizontalAdvance(s) for s in lines);bh=line_h*len(lines)
            def block(x,y):
                ctx.check();painter.save()
                try:
                    painter.setOpacity(opacity);painter.translate(x,y);painter.rotate(angle)
                    for j,line in enumerate(lines):
                        path=QPainterPath();bounds=metrics.boundingRect(line)
                        path.addText(-metrics.horizontalAdvance(line)/2,-(len(lines)-1)*line_h/2+j*line_h-(bounds.top()+bounds.bottom())/2,font,line)
                        if shadow:
                            painter.save();painter.translate(max(1,size*.05),max(1,size*.05));painter.fillPath(path,QColor(0,0,0,90));painter.restore()
                        if stroke>0:
                            pen=QPen(QColor(settings['stroke_color']),stroke);pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin);painter.strokePath(path,pen)
                        painter.fillPath(path,QColor(settings['fill']))
                finally:painter.restore()
            if tile:
                sx=max(bw+spacing*1.8,size*7);sy=max(bh+spacing*1.35,size*5);y=-sy
                while y<h+sy:
                    x=-sx
                    while x<w+sx:block(x,y);x+=sx
                    y+=sy
            else:
                margin=base*settings['margin']/100;r,c=divmod(settings['position'],3)
                # 使用旋转后的包围框定位，避免角落水印被裁掉。
                radians=math.radians(angle);half_w=(abs(bw*math.cos(radians))+abs(bh*math.sin(radians)))/2;half_h=(abs(bw*math.sin(radians))+abs(bh*math.cos(radians)))/2
                block([margin+half_w,w/2,w-margin-half_w][c],[margin+half_h,h/2,h-margin-half_h][r])
        if lines:
            size=max(12,round(base*settings['size']/100))
            layer(size,settings['opacity']/100,settings['angle'],base*settings['spacing']/100,size*settings['stroke'],settings['shadow'],settings['mode']=='平铺')
            if settings['protect']:layer(max(10,round(base*.026)),.18,-28,base*.1,0,False,True)
    finally:painter.end()
    ctx.check();return image

def export(ctx,source,out,settings):
    if not source or not Path(source).is_file():raise ValueError('请先选择图片。')
    if not out.strip():raise ValueError('请选择保存文件夹。')
    ctx.log('正在按原始分辨率绘制水印…');image=render(ctx,source,settings);ctx.progress(60)
    image=image.convertToFormat(QImage.Format.Format_RGBA8888)
    pil=Image.frombytes('RGBA',(image.width(),image.height()),bytes(image.constBits()),'raw','RGBA',image.bytesPerLine())
    if settings['hidden']:
        ctx.log('正在写入隐形像素水印…');pil=embed(pil,settings['hidden_text'].strip() or settings['text'].strip(),settings['key'])
    extension='png' if settings['hidden'] else {'PNG':'png','JPG':'jpg','WEBP':'webp'}[settings['format']]
    folder=Path(out);folder.mkdir(parents=True,exist_ok=True);name=Path(source).stem+'_watermark';target=folder/f'{name}.{extension}';i=2
    while target.exists():target=folder/f'{name}_{i}.{extension}';i+=1
    if extension=='jpg':
        background=Image.new('RGB',pil.size,'white');background.paste(pil,mask=pil.getchannel('A'));pil=background
    ctx.check()
    try:
        with target.open('xb') as file:
            pil.save(file,format={'png':'PNG','jpg':'JPEG','webp':'WEBP'}[extension],**({'quality':95} if extension!='png' else {}))
    except Exception:
        if target.exists() and target.stat().st_size==0:target.unlink()
        raise
    ctx.progress(100);return target

def verify(ctx,source,key):
    if not source or not Path(source).is_file():raise ValueError('请先导入需要验证的图片。')
    with Image.open(source) as image:result=read_hidden(image,key)
    ctx.check();return result
