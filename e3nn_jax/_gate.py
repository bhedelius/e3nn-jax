from e3nn_jax import ScalarActivation, ElementwiseTensorProduct, Irreps


class Gate:
    r"""Gate activation function.

    The gate activation is a direct sum of two sets of irreps. The first set
    of irreps is ``irreps_scalars`` passed through activation functions
    ``act_scalars``. The second set of irreps is ``irreps_gated`` multiplied
    by the scalars ``irreps_gates`` passed through activation functions
    ``act_gates``. Mathematically, this can be written as:

    .. math::
        \left(\bigoplus_i \phi_i(x_i) \right) \oplus \left(\bigoplus_j \phi_j(g_j) y_j \right)

    where :math:`x_i` and :math:`\phi_i` are from ``irreps_scalars`` and
    ``act_scalars``, and :math:`g_j`, :math:`\phi_j`, and :math:`y_j` are
    from ``irreps_gates``, ``act_gates``, and ``irreps_gated``.

    The parameters passed in should adhere to the following conditions:

    1. ``len(irreps_scalars) == len(act_scalars)``.
    2. ``len(irreps_gates) == len(act_gates)``.
    3. ``irreps_gates.num_irreps == irreps_gated.num_irreps``.

    Parameters
    ----------
    irreps_scalars : `e3nn.o3.Irreps`
        Representation of the scalars that will be passed through the
        activation functions ``act_scalars``.

    act_scalars : list of function or None
        Activation functions acting on the scalars.

    irreps_gates : `e3nn.o3.Irreps`
        Representation of the scalars that will be passed through the
        activation functions ``act_gates`` and multiplied by the
        ``irreps_gated``.

    act_gates : list of function or None
        Activation functions acting on the gates. The number of functions in
        the list should match the number of irrep groups in ``irreps_gates``.

    irreps_gated : `e3nn.o3.Irreps`
        Representation of the gated tensors.
        ``irreps_gates.num_irreps == irreps_gated.num_irreps``

    Examples
    --------
    >>> import jax.numpy as jnp
    >>> g = Gate("16x0o", [jnp.tanh], "32x0o", [jnp.tanh], "16x1e+16x1o")
    >>> g.irreps_out
    16x0o+16x1o+16x1e
    """
    irreps_in: Irreps
    irreps_out: Irreps

    def __init__(self, irreps_scalars, act_scalars, irreps_gates, act_gates, irreps_gated):
        super().__init__()
        irreps_scalars = Irreps(irreps_scalars)
        irreps_gates = Irreps(irreps_gates)
        irreps_gated = Irreps(irreps_gated)

        if len(irreps_gates) > 0 and irreps_gates.lmax > 0:
            raise ValueError(f"Gate scalars must be scalars, instead got irreps_gates = {irreps_gates}")
        if len(irreps_scalars) > 0 and irreps_scalars.lmax > 0:
            raise ValueError(f"Scalars must be scalars, instead got irreps_scalars = {irreps_scalars}")
        if irreps_gates.num_irreps != irreps_gated.num_irreps:
            raise ValueError(f"There are {irreps_gated.num_irreps} irreps in irreps_gated, but a different number ({irreps_gates.num_irreps}) of gate scalars in irreps_gates")

        # self.sc = _SortCut(irreps_scalars, irreps_gates, irreps_gated)
        self.irreps_scalars, self.irreps_gates, self.irreps_gated = irreps_scalars, irreps_gates, irreps_gated  # self.sc.irreps_outs
        self.irreps_in = irreps_scalars + irreps_gates + irreps_gated

        self.act_scalars = ScalarActivation(irreps_scalars, act_scalars)
        irreps_scalars = self.act_scalars.irreps_out

        self.act_gates = ScalarActivation(irreps_gates, act_gates)
        irreps_gates = self.act_gates.irreps_out

        self.mul = ElementwiseTensorProduct(irreps_gated, irreps_gates)
        irreps_gated = self.mul.irreps_out

        self.irreps_out = irreps_scalars + irreps_gated

    def __repr__(self):
        return f"{self.__class__.__name__} ({self.irreps_in} -> {self.irreps_out})"

    def __call__(self, features):
        """Evaluate the gated activation function.

        Parameters
        ----------
        features : `torch.Tensor`
            tensor of shape ``(irreps_in.dim)``

        Returns
        -------
        `torch.Tensor`
            tensor of shape ``(irreps_out.dim)``
        """
        features = self.irreps_in.as_list(features)
        scalars = features[:len(self.irreps_scalars)]
        gates = features[len(self.irreps_scalars): -len(self.irreps_gated)]
        gated = features[-len(self.irreps_gated):]

        scalars = self.act_scalars(scalars)
        if gates:
            gates = self.act_gates(gates)
            gated = self.mul.left_right(gated, gates, output_list=True)
            features = scalars + gated
        else:
            features = scalars
        return features
