from pdf_utils import html_to_pdf

html = "<html><body><h1>Hello PDF</h1></body></html>"
html_to_pdf(html, "output/test.pdf")
print("Created output/test.pdf")
