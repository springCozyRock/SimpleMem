"""
simplemem.optimize() — user-facing config optimization entry point.

Wraps EvolveMem's evolution loop into a simple interface:
    config = simplemem.optimize(mem, dev_questions, max_rounds=7)
    config.save("my_config.json")
"""

from typing import List, Tuple
from simplemem.config import Config


def run_optimization(
    mem,
    dev_questions: List[Tuple[str, str]],
    max_rounds: int = 7,
    **kwargs,
) -> Config:
    """
    Run EvolveMem's self-evolution loop on a dev set to find
    the best retrieval configuration.

    Args:
        mem: SimpleMem instance with memories already loaded
        dev_questions: list of (question, ground_truth_answer) tuples
        max_rounds: maximum evolution rounds

    Returns:
        Config with optimized parameters
    """
    from simplemem.optimizer.evolution import EvolutionEngine, EvolutionConfig

    # Set up evolution config
    evo_config = EvolutionConfig(
        max_rounds=max_rounds,
        **{k: v for k, v in kwargs.items() if hasattr(EvolutionConfig, k)},
    )

    # Run evolution
    engine = EvolutionEngine(config=evo_config)
    result = engine.run(
        memory_store=mem._backend if hasattr(mem, '_backend') else mem,
        qa_pairs=dev_questions,
    )

    # Convert EvolveMem's result to a SimpleMem Config
    best = result.best_config if hasattr(result, 'best_config') else {}

    config = Config(
        k_sem=best.get("semantic_top_k", 0),
        k_kw=best.get("keyword_top_k", 5),
        k_str=best.get("structured_top_k", 0),
        context_budget=best.get("max_context", 8),
        fusion_mode=best.get("fusion_mode", "sum"),
        fusion_weights=best.get("fusion_weights", {
            "semantic": 1.0, "keyword": 1.0, "structured": 1.0,
        }),
        answer_style=best.get("answer_style", "concise"),
        enable_entity_swap=best.get("enable_entity_swap", False),
        enable_query_decomposition=best.get("enable_query_decomposition", False),
        enable_answer_verification=best.get("enable_answer_verification", False),
        category_overrides=best.get("per_category_overrides", {}),
        evolved=True,
        evolution_rounds=result.rounds_completed if hasattr(result, 'rounds_completed') else max_rounds,
        source_benchmark=kwargs.get("benchmark_name", ""),
    )

    return config
