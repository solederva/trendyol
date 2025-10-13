from lxml import etree

# WG ile başlayan ürünleri kaldır
input_path = 'data/source.xml'
output_path = 'data/source_chekich.xml'

tree = etree.parse(input_path)
root = tree.getroot()

for product in root.xpath("//Product[starts-with(ProductCode, 'WG')]"):
    root.remove(product)

tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)
print(f"WG ile başlayan ürünler kaldırıldı: {output_path}")
