import numpy as np
import tensorflow as tf

from pararealml.operators.ml.supervised import SKLearnKerasRegressor
from pararealml.utils.rand import SEEDS, set_random_seed
from pararealml.utils.tf import use_deterministic_ops
from pararealml.utils.time import time


def build_model() -> tf.keras.Model:
    sml_model.compile(
        optimizer=tf.optimizers.Adam(
            learning_rate=tf.optimizers.schedules.ExponentialDecay(
                1e-3, decay_steps=25000 * 21, decay_rate=5e-3
            )
        ),
        loss="mse",
    )
    return sml_model


if __name__ == "__main__":
    set_random_seed(SEEDS[0])

    use_deterministic_ops()

    from experiments.burgers.operators import coarse_sml, sml_model

    sml_data = (
        np.load("data/sml_features.npy"),
        np.load("data/sml_labels.npy"),
    )
    batch_size = int(4 * 325 * 21 * 21 * 0.9 * 0.8 / 21)
    sml_train_loss, sml_test_loss = time("sml model fitting")(
        coarse_sml.fit_model
    )(
        SKLearnKerasRegressor(
            build_model,
            batch_size=batch_size,
            epochs=25000,
            verbose=True,
            validation_split=0.2,
            callbacks=[
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_loss",
                    min_delta=0,
                    patience=6250,
                    restore_best_weights=True,
                )
            ],
            max_predict_batch_size=batch_size,
        ),
        sml_data,
        test_size=0.1,
    )[
        0
    ]
    print("sml train loss:", sml_train_loss)
    print("sml test loss:", sml_test_loss)
    coarse_sml.model.model.save_weights("weights/sml")
