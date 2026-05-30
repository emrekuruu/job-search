from job_search.space.ui import build_app

demo = build_app()
demo.queue(default_concurrency_limit=4)

if __name__ == "__main__":
    demo.launch(share=True)
