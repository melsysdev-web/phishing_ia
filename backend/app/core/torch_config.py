import torch


def configure() -> None:
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
