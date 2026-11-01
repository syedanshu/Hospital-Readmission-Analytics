import pandas as pd

from src.train_model import GROUP, TARGET, _group_split


def test_patient_groups_do_not_cross_dataset_partitions():
    frame = pd.DataFrame({
        GROUP: [f"patient-{patient}" for patient in range(100) for _ in range(2)],
        TARGET: [patient % 2 for patient in range(100) for _ in range(2)],
    })

    train, validation, test = _group_split(frame)
    train_groups = set(train[GROUP])
    validation_groups = set(validation[GROUP])
    test_groups = set(test[GROUP])

    assert train_groups.isdisjoint(validation_groups)
    assert train_groups.isdisjoint(test_groups)
    assert validation_groups.isdisjoint(test_groups)
