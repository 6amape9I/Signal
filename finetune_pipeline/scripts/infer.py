try:
    from finetune_pipeline.inference import main
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from finetune_pipeline.inference import main


if __name__ == "__main__":
    main()

