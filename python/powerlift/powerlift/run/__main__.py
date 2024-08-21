""" This is called to run a trial by worker nodes (local / remote). """


def run_trials(
    experiment_id, trial_ids, db_url, timeout, raise_exception, debug_fn=None
):
    """Runs trials. Includes wheel installation and timeouts."""
    from powerlift.bench.store import Store
    import traceback
    from powerlift.executors.base import timed_run
    from powerlift.bench.store import MIMETYPE_FUNC, BytesParser
    from powerlift.bench.experiment import Store
    import subprocess
    import tempfile
    from pathlib import Path
    import sys

    store = Store(db_url)
    while True:
        # TODO: remove the trial_ids that we no longer use.
        trial_id = store.pick_trial()
        if trial_id is None:
            break  # no more work left

        trial = store.find_trial_by_id(trial_id)
        if trial is None:
            raise RuntimeError(f"No trial found for id {trial_id}")

        # Handle input assets
        trial_run_fn = None
        for input_asset in trial.input_assets:
            if input_asset.mimetype == MIMETYPE_FUNC:
                trial_run_fn = BytesParser.deserialize(
                    MIMETYPE_FUNC, input_asset.embedded
                )
            else:
                continue
        if debug_fn is not None:
            trial_run_fn = debug_fn

        if trial_run_fn is None:
            raise RuntimeError("No trial run function found.")

        # Run trial
        errmsg = None
        try:
            _, duration, timed_out = timed_run(
                lambda: trial_run_fn(trial), timeout_seconds=timeout
            )
            if timed_out:
                raise RuntimeError(f"Timeout failure ({duration})")
        except Exception as e:
            errmsg = traceback.format_exc()
            if raise_exception:
                raise e
        finally:
            store.end_trial(trial.id, errmsg)


if __name__ == "__main__":
    import os

    experiment_id = os.getenv("EXPERIMENT_ID")
    trial_ids = os.getenv("TRIAL_IDS").split(",")
    db_url = os.getenv("DB_URL")
    timeout = float(os.getenv("TIMEOUT", 0.0))
    raise_exception = True if os.getenv("RAISE_EXCEPTION", False) == "True" else False

    run_trials(experiment_id, trial_ids, db_url, timeout, raise_exception)
