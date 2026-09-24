from mainnet_attack_gym.eip7702 import authority

# A real Poisoner delegation from mainnet tx 0x6267fde1…15da. The recovered EOA's
# on-chain code was checked to be 0xef0100 || 0xe6b9…43ed (the 7702 delegation marker).
AUTH = {"chainId": "0x1", "address": "0xe6b97aa1490c93c28a14d86c13c9dc9c950643ed", "nonce": "0x6",
        "yParity": "0x0", "r": "0x5647eceb58b1e9cfcc8eaf4c12a629ae9e61c2c9f825ce3c73f8de561bf26236",
        "s": "0x345cbb5a68d1b3939413f9a14a81d00f9e742ed13191d586de9e8da40150b6ef"}


def test_recovers_the_delegating_eoa():
    assert authority(AUTH) == "0x1c4037d12a4d0fe52d45596e932a8aefcd151b3b"
