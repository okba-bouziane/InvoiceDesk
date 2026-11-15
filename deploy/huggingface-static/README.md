---
title: InvoiceDesk
colorFrom: green
colorTo: gray
sdk: static
pinned: false
short_description: Read supplier invoices and ask questions, in your browser
---

Drop a photo of a supplier invoice and get the fields a bookkeeper types in (supplier, NIF, RC, number, date, client, lines, HT, TVA, TTC), with the totals recalculated, then ask questions about it in French or English.

The model, [okba-bouziane/invoicedesk-donut](https://huggingface.co/okba-bouziane/invoicedesk-donut), runs in your browser: Donut fine-tuned for invoices, quantised to 8 bits (about 280 MB, downloaded once). Invoices never leave the device.

The 8-bit copy is a little less accurate than the full model on the same test invoices: field F1 0.964 against 0.968 on the training layouts, and 0.620 against 0.700 on a layout it never saw. Reading one invoice takes several seconds, depending on the device. The sample invoices are generated. Code and evaluation: https://github.com/okba-bouziane/InvoiceDesk
