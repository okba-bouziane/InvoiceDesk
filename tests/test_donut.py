from invoicedesk import donut


def test_label_round_trips_through_the_token_sequence():
    label = {
        "vendor": "SARL Atlas",
        "total_ttc": "22 812,89",
        "items": [
            {"name": "Ciment CPJ 42.5 (sac 50 kg)", "qty": "10", "unit_price": "900,00", "amount": "9 000,00"},
            {"name": "Plâtre", "qty": "2", "unit_price": "500,00", "amount": "1 000,00"},
        ],
    }
    keys: set[str] = set()
    seq = donut.json2token(label, keys)
    assert "<s_vendor>" in keys and "</s_items>" in keys
    assert donut.token2json(seq) == label


def test_a_single_item_is_still_a_list():
    label = {"items": [{"name": "Filtre", "qty": "1", "unit_price": "900,00", "amount": "900,00"}]}
    assert donut.token2json(donut.json2token(label)) == label


def test_truncated_output_keeps_the_complete_fields():
    seq = "<s_vendor>SARL Atlas</s_vendor><s_total_ttc>12 3"
    assert donut.token2json(seq) == {"vendor": "SARL Atlas"}


def test_question_prompt_and_answer_parsing():
    seq = donut.qa_target("Quel est le NIF ?", "123456789012345")
    assert seq.startswith(donut.qa_prompt("Quel est le NIF ?"))
    assert donut.parse_answer(seq + "</s>") == "123456789012345"


def test_generated_task_token_is_removed():
    assert donut.clean_generated("<s_dzinv><s_tva>19</s_tva></s><pad>", "</s>", "<pad>") == "<s_tva>19</s_tva>"
