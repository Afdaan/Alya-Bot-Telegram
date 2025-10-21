from typing import Literal
from config.settings import DEFAULT_LANGUAGE


def analyze_response(lang: Literal['id', 'en'] = DEFAULT_LANGUAGE) -> str:
    """Return a helpful response explaining how to use the analysis feature.
    
    Args:
        lang: The language for the response ('id' or 'en').
        
    Returns:
        The help message string.
    """
    if lang == 'id':
        return """<b>🔍 Analisis dengan Alya</b>

<i>[merapikan kacamatanya dengan anggun]</i>

Alya dapat menganalisis berbagai jenis konten dengan detail dan wawasan. Gunakan perintah berikut:

• <code>!ask [teks]</code> - Analisis teks atau pertanyaan
• <code>!ask</code> + <i>balas ke gambar</i> - Analisis visual gambar
• <code>!ask</code> + <i>balas ke dokumen</i> - Analisis isi dokumen

<b>Contoh:</b>
<code>!ask Apa itu machine learning?</code>
<code>!ask</code> + lampirkan gambar
<code>!ask</code> + lampirkan dokumen PDF

<i>[menyibakkan rambut ke belakang]</i>

Hmph! Jangan berpikir Alya senang melakukan ini untukmu. Alya hanya membantu karena kemampuan analisis Alya yang luar biasa! 💫"""
    else:
        return """<b>🔍 Analysis with Alya</b>

<i>[adjusts her glasses gracefully]</i>

Alya can analyze various types of content with detail and insight. Use the following commands:

• <code>!ask [text]</code> - Analyze text or questions
• <code>!ask</code> + <i>reply to image</i> - Visual image analysis
• <code>!ask</code> + <i>reply to document</i> - Document content analysis

<b>Examples:</b>
<code>!ask What is machine learning?</code>
<code>!ask</code> + attach an image
<code>!ask</code> + attach a PDF document

<i>[brushes hair back]</i>

Hmph! Don't think Alya enjoys doing this for you. Alya is only helping because of her extraordinary analytical capabilities! 💫"""