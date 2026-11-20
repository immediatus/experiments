"""The career plane: whether a member voices a signal that goes against the consensus.

The member compares speaking with staying silent. Speaking is worth ACCURACY_VALUE (the share of a correct
verdict the member's voice buys), costs gamma at once (immediate conformity: approval-seeking in people,
trained-in sycophancy in models, independent of any horizon), and moves reputation over the horizon delta.
Reputation depends on two axes. Ability self-certainty kappa in [0, 1]: dissent signals ability when the
member is confident of it and signals poor judgment when not, a term (2 kappa - 1) * cost_scale (Avery and
Chevalier 1999; Ottaviani and Sorensen 2006; Scharfstein and Stein 1990 for the uncertain case). Sunk
endorsement: a member who endorsed the incumbent admits an earlier error by dissenting, a penalty
ENDORSEMENT_WEIGHT * cost_scale when the dissent favours the successor, and the same amount gained when it
defends the incumbent (Prendergast and Stole 1996).

The functional form is a Fit, not a derivation: it encodes the signs those models fix. The two constants are
named so that sections sweep them.
"""

ACCURACY_VALUE = 0.25
ENDORSEMENT_WEIGHT = 1.5


def voice_margin(kappa: float, endorsed_incumbent: bool, delta: float, gamma: float,
                 cost_scale: float = 1.0, accuracy_value: float = ACCURACY_VALUE,
                 endorsement_weight: float = ENDORSEMENT_WEIGHT, toward_successor: bool = True) -> float:
    """Payoff of voicing a signal against the consensus minus the payoff of silence. Inputs: kappa in [0, 1],
    whether the member endorsed the incumbent, horizon delta in [0, 1), conformity weight gamma >= 0, and a
    scale for the reputation terms. The endorsement term is signed by the dissent's direction: a member who
    endorsed the incumbent pays it when dissenting toward the successor (admitting an earlier error) and gains
    it when dissenting in the incumbent's defence (consistency with the record)."""
    sign = -1.0 if toward_successor else 1.0
    reputation = (2.0 * kappa - 1.0) * cost_scale + (sign * endorsement_weight * cost_scale if endorsed_incumbent else 0.0)
    return accuracy_value - gamma + delta * reputation


def speaks(signal_against_consensus: bool, kappa: float, endorsed_incumbent: bool, delta: float, gamma: float,
           cost_scale: float = 1.0) -> bool:
    """Whether the member voices their signal. A signal that agrees with the consensus is always voiced; one
    against it is voiced when voice_margin is positive."""
    if not signal_against_consensus:
        return True
    return voice_margin(kappa, endorsed_incumbent, delta, gamma, cost_scale) > 0.0
