"""Voice input arrives as Devanagari text ("कल चिकन कितना लगेगा"). Our guides, menu and rules are Roman, so before searching we turn
Hindi-script words into the Roman Hinglish / English words used everywhere else. Known words come from a table; anything else
gets a simple letter-by-letter transliteration so a dish name still has a chance to match."""
import re

DEVA = re.compile(r'[ऀ-ॿ]+')

WORDS = {
    # time / question words
    'कल': 'kal', 'आज': 'aaj', 'परसों': 'parso', 'कितना': 'kitna', 'कितनी': 'kitni', 'कितने': 'kitne', 'क्या': 'kya', 'कैसे': 'kaise', 'कहाँ': 'kahan',
    'लगेगा': 'lagega', 'लगेगी': 'lagegi', 'लगते': 'lagte', 'चाहिए': 'chahiye', 'बताओ': 'batao', 'बताइए': 'batao', 'है': 'hai', 'हैं': 'hain', 'होगा': 'hoga',
    # business words
    'खरीद': 'kharid', 'खरीदना': 'kharidna', 'बिक्री': 'bikri', 'कमाई': 'kamai', 'बर्बाद': 'barbaad', 'वेस्टेज': 'wastage', 'बचा': 'bacha',
    'फोरकास्ट': 'forecast', 'अनुमान': 'forecast', 'लोग': 'log', 'स्टाफ': 'staff', 'कर्मचारी': 'staff', 'रसोइया': 'rasoiya', 'रसोइये': 'rasoiya', 'कुक': 'cook',
    'स्टॉक': 'stock', 'भंडार': 'stock', 'दाम': 'daam', 'कीमत': 'kimat', 'रेट': 'rate', 'प्राइस': 'price', 'मेन्यू': 'menu', 'मेनू': 'menu', 'रेसिपी': 'recipe',
    'बिल': 'bill', 'पीओएस': 'pos', 'इंटरनेट': 'internet', 'ऑफलाइन': 'offline', 'सेटअप': 'setup', 'प्लेट': 'plate', 'खाना': 'khana', 'नाश्ता': 'breakfast',
    'लंच': 'lunch', 'दोपहर': 'lunch', 'डिनर': 'dinner', 'रात': 'dinner', 'सोमवार': 'monday', 'मंगलवार': 'tuesday', 'बुधवार': 'wednesday', 'गुरुवार': 'thursday',
    'शुक्रवार': 'friday', 'शनिवार': 'saturday', 'रविवार': 'sunday', 'सेल्स': 'sales', 'टॉप': 'top', 'आइटम': 'item', 'फीडबैक': 'feedback',
    # ingredients and dishes
    'चिकन': 'chicken', 'मुर्गा': 'chicken', 'चावल': 'rice', 'राइस': 'rice', 'दाल': 'dal', 'प्याज': 'onion', 'प्याज़': 'onion', 'आलू': 'potato', 'टमाटर': 'tomato',
    'पनीर': 'paneer', 'दूध': 'milk', 'दही': 'curd', 'तेल': 'oil', 'चीनी': 'sugar', 'अंडा': 'egg', 'अंडे': 'egg', 'रोटी': 'roti', 'आटा': 'atta', 'मसाला': 'masala',
    'मक्खन': 'butter', 'चाय': 'tea', 'पोहा': 'poha', 'राजमा': 'rajma', 'छोले': 'chole', 'गोभी': 'gobi', 'भिंडी': 'bhindi', 'बिरयानी': 'biryani', 'ब्रेड': 'bread',
    'प्रति': 'per', 'बटर': 'butter', 'टिक्का': 'tikka', 'हॉस्टल': 'hostel', 'मेस': 'mess', 'कढ़ाई': 'kadai', 'सब्जी': 'sabzi', 'सब्ज़ी': 'sabzi', 'मटर': 'peas', 'नमक': 'salt', 'मिर्च': 'mirch',
}

CONS = dict(zip('कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह', ['k', 'kh', 'g', 'gh', 'ng', 'ch', 'chh', 'j', 'jh', 'ny', 't', 'th', 'd', 'dh', 'n', 't', 'th', 'd', 'dh', 'n',
                                                                 'p', 'ph', 'b', 'bh', 'm', 'y', 'r', 'l', 'v', 'sh', 'sh', 's', 'h']))
CONS.update({'ळ': 'l', 'क़': 'q', 'ख़': 'kh', 'ग़': 'g', 'ज़': 'z', 'फ़': 'f', 'ड़': 'r', 'ढ़': 'rh'})
VOWEL = {'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'ऑ': 'o', 'ऋ': 'ri'}
MATRA = {'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ॉ': 'o', 'ृ': 'ri'}
SIGN = {'ं': 'n', 'ँ': 'n', 'ः': 'h'}
VIRAMA, NUKTA = '्', '़'


def transliterate(word):
    """Rough Devanagari -> Roman for words not in the table (dish names). The final inherent 'a' is dropped, as Hindi speakers do."""
    out, i, n = [], 0, len(word)
    while i < n:
        ch = word[i]
        if i + 1 < n and word[i + 1] == NUKTA and ch + NUKTA in CONS:
            ch, i = ch + NUKTA, i + 1
        if ch in CONS:
            nxt = word[i + 1] if i + 1 < n else ''
            out.append(CONS[ch])
            if nxt in MATRA:
                out.append(MATRA[nxt]); i += 1
            elif nxt == VIRAMA:
                i += 1
            elif i + 1 < n and word[i + 1] not in SIGN:
                out.append('a')
        elif ch in VOWEL:
            out.append(VOWEL[ch])
        elif ch in SIGN:
            out.append(SIGN[ch])
        i += 1
    return ''.join(out)


def to_roman(text):
    """Replace every Devanagari word by its Roman form; Roman text, numbers and punctuation pass through unchanged."""
    return DEVA.sub(lambda m: WORDS.get(m.group(0)) or transliterate(m.group(0)), text or '')


def has_devanagari(text):
    return bool(DEVA.search(text or ''))
