import json
import re
import threading
import textwrap
from urllib import parse, request

class TextWrapperApp:

    def detect_language(self, text):
        """自动检测文本语言"""
        if not text.strip():
            return 'auto'
        chinese_chars = len(re.findall('[\\u4e00-\\u9fff]', text))
        english_chars = len(re.findall('[a-zA-Z]', text))
        total_chars = len(text.replace('\n', '').replace(' ', ''))
        if total_chars == 0:
            return 'auto'
        chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
        if chinese_ratio > 0.8:
            return '中文'
        elif chinese_ratio < 0.2:
            return '英文'
        else:
            return '混合'

    def _translate_to_chinese(self, text):
        """按可用服务顺序翻译英文到中文"""
        errors = []
        for service_name, translator in (('LibreTranslate', self._translate_via_libretranslate), ('MyMemory', self._translate_via_mymemory)):
            try:
                translated_text = translator(text)
                if translated_text.strip():
                    return (translated_text.strip(), service_name)
                errors.append(f'{service_name} 未返回有效结果')
            except Exception as e:
                errors.append(f'{service_name}: {str(e)}')
        raise RuntimeError('；'.join(errors) if errors else '翻译服务不可用')

    def _split_text_for_translation(self, text, max_chars=350):
        """把长文本切成适合翻译接口的小块，尽量保留段落和句子边界。"""
        chunks = []
        for paragraph in text.split('\n'):
            if not paragraph.strip():
                chunks.append('')
                continue
            sentence_buffer = []
            current = ''
            sentences = re.split('(?<=[.!?])\\s+', paragraph.strip())
            if len(sentences) == 1:
                sentences = [paragraph.strip()]
            for sentence in sentences:
                if len(sentence) > max_chars:
                    if current:
                        sentence_buffer.append(current)
                        current = ''
                    words = sentence.split()
                    if not words:
                        words = [sentence]
                    word_current = ''
                    for word in words:
                        candidate = f'{word_current} {word}'.strip()
                        if len(candidate) <= max_chars:
                            word_current = candidate
                        else:
                            if word_current:
                                sentence_buffer.append(word_current)
                                word_current = ''
                            if len(word) <= max_chars:
                                word_current = word
                            else:
                                start = 0
                                while start < len(word):
                                    sentence_buffer.append(word[start:start + max_chars])
                                    start += max_chars
                    if word_current:
                        sentence_buffer.append(word_current)
                    continue
                candidate = f'{current} {sentence}'.strip() if current else sentence
                if len(candidate) <= max_chars:
                    current = candidate
                else:
                    if current:
                        sentence_buffer.append(current)
                    current = sentence
            if current:
                sentence_buffer.append(current)
            chunks.extend(sentence_buffer)
        return chunks

    def _translate_chunked_text(self, text, translator):
        """分段翻译并合并结果，避免单次请求过长。"""
        translated_paragraphs = []
        paragraph = []
        for chunk in self._split_text_for_translation(text):
            if chunk == '':
                if paragraph:
                    translated_paragraphs.append(' '.join(paragraph).strip())
                    paragraph = []
                translated_paragraphs.append('')
                continue
            translated_paragraph = translator(chunk).strip()
            if translated_paragraph:
                paragraph.append(translated_paragraph)
        if paragraph:
            translated_paragraphs.append(' '.join(paragraph).strip())
        return '\n'.join(translated_paragraphs).strip()

    def _translate_via_libretranslate(self, text):
        """使用 LibreTranslate 把英文翻译为中文"""
        return self._translate_chunked_text(text, self._libretranslate_single_chunk)

    def _libretranslate_single_chunk(self, text):
        """单次调用 LibreTranslate 接口。"""
        data = parse.urlencode({'q': text, 'source': 'en', 'target': 'zh', 'format': 'text'}).encode('utf-8')
        req = request.Request('https://libretranslate.com/translate', data=data, headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'})
        with request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode('utf-8'))
        if isinstance(payload, dict) and payload.get('error'):
            raise RuntimeError(payload['error'])
        translated_text = payload.get('translatedText', '').strip()
        if not translated_text:
            raise RuntimeError('未返回翻译结果')
        return translated_text

    def _translate_via_mymemory(self, text):
        """使用 MyMemory 作为备用翻译服务"""
        return self._translate_chunked_text(text, self._mymemory_single_chunk)

    def _mymemory_single_chunk(self, text):
        """单次调用 MyMemory 接口。"""
        last_error = None
        for langpair in ('en|zh-CN', 'en|zh'):
            try:
                url = 'https://api.mymemory.translated.net/get?' + parse.urlencode({'q': text, 'langpair': langpair})
                req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with request.urlopen(req, timeout=20) as response:
                    payload = json.loads(response.read().decode('utf-8'))
                translated_text = payload.get('responseData', {}).get('translatedText', '').strip()
                if translated_text:
                    return translated_text
                last_error = '未返回翻译结果'
            except Exception as e:
                last_error = str(e)
        raise RuntimeError(last_error or '翻译失败')

    def advanced_text_wrap(self, text, width=80, language='auto', keep_paragraphs=True, break_long_words=True):
        """高级文字换行函数"""
        if keep_paragraphs:
            paragraphs = text.split('\n')
            wrapped_paragraphs = []
            for para in paragraphs:
                if para.strip():
                    if language == '中文':
                        wrapped = self.wrap_chinese(para, width)
                    elif language == '英文':
                        wrapper = textwrap.TextWrapper(width=width, break_long_words=break_long_words, break_on_hyphens=True)
                        wrapped = wrapper.fill(para)
                    else:
                        wrapper = textwrap.TextWrapper(width=width, break_long_words=True, break_on_hyphens=True)
                        wrapped = wrapper.fill(para)
                    wrapped_paragraphs.append(wrapped)
                else:
                    wrapped_paragraphs.append('')
            return '\n'.join(wrapped_paragraphs)
        elif language == '中文':
            return self.wrap_chinese(text, width)
        else:
            wrapper = textwrap.TextWrapper(width=width, break_long_words=break_long_words, break_on_hyphens=True)
            return wrapper.fill(text)

    def wrap_chinese(self, text, width):
        """中文换行函数（按字符换行）"""
        result = []
        lines = text.split('\n')
        for line in lines:
            if not line.strip():
                result.append('')
                continue
            chars = list(line)
            current_line = []
            current_length = 0
            for char in chars:
                char_width = 2 if '一' <= char <= '鿿' else 1
                if current_length + char_width > width:
                    result.append(''.join(current_line))
                    current_line = [char]
                    current_length = char_width
                else:
                    current_line.append(char)
                    current_length += char_width
            if current_line:
                result.append(''.join(current_line))
        return '\n'.join(result)

def main():
    """主函数"""
    root = tk.Tk()
    app = TextWrapperApp(root)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root.mainloop()
