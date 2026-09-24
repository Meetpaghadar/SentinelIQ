from dataclasses import dataclass

ESSAY = "JP Essay Writing"
NLP = "NLP standford"
UPSKILL = "Advice on Upskilling"


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    question: str
    expected_documents: tuple[str, ...]
    answerable: bool
    expected_path: str = "normal"


FROZEN_CASES = [
    EvaluationCase("What advice is given about writing?", (ESSAY,), True),
    EvaluationCase("What advice is given about improving memory while writing?", (ESSAY,), True),
    EvaluationCase("What is a large language model?", (NLP,), True),
    EvaluationCase("What is perplexity in language modeling?", (NLP,), True),
    EvaluationCase("What advice is given about upskilling?", (UPSKILL,), True),
    EvaluationCase("How do I configure an AWS VPC with Terraform?", (), False),
]

HARDER_CASES = [
    EvaluationCase("any tips for writing better?", (ESSAY,), True),
    EvaluationCase("next-token prediction systems", (NLP,), True),
    EvaluationCase("what's PPL?", (NLP,), True),
    EvaluationCase("why put thoughts outside your head?", (ESSAY,), True),
    EvaluationCase(
        "How do writing things down and deliberate practice both help someone improve?",
        (ESSAY, UPSKILL),
        True,
    ),
    EvaluationCase(
        "How should I improve my drafts and my professional skills?",
        (ESSAY, UPSKILL),
        True,
    ),
    EvaluationCase(
        (
            "I have been debugging Kubernetes ingress and Terraform AWS VPC modules all week, "
            "but I actually need to know how language-model quality is scored with perplexity."
        ),
        (NLP,),
        True,
    ),
    EvaluationCase(
        "What is the difference between writing to remember and practicing to improve performance?",
        (ESSAY, UPSKILL),
        True,
    ),
    EvaluationCase(
        "What do the sources say about evaluating language models versus improving human writing?",
        (NLP, ESSAY),
        True,
    ),
    EvaluationCase("the memory filter trick after finishing an essay", (ESSAY,), True),
    EvaluationCase(
        (
            "outline headings, a 25 percent longer first draft, "
            "and reconstructing the argument from memory"
        ),
        (ESSAY,),
        True,
    ),
    EvaluationCase(
        "How are large language models and deliberate practice described?",
        (NLP, UPSKILL),
        True,
    ),
    EvaluationCase(
        (
            "Hey, my manager asked about kubernetes ingress certificates and also what advice "
            "exists about upskilling."
        ),
        (UPSKILL,),
        True,
    ),
    EvaluationCase(
        "Compare perplexity and human judgment for evaluating language models.",
        (NLP,),
        True,
    ),
    EvaluationCase("NNs that emit next-word distributions", (NLP,), True),
    EvaluationCase("What is the company's 2024 MFA policy?", (), False),
]
