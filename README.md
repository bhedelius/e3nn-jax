# e3nn-jax

:construction: :construction: :construction:
Disclamier: This is a work in progress. No part of the library can be considered stable.

## Example

Example with the `Irreps` class.
This class specifies a direct sum of irreducible representations.
It does not contain any actual data. It is use to specify the "type" of the data under rotation.

```python
from e3nn_jax import Irreps

irreps = Irreps("2x0e + 3x1e")  # 2 even scalars and 3 even vectors
irreps = irreps + irreps  # 2x0e+3x1e+2x0e+3x1e
irreps.D_from_angles(alpha=1.57, beta=1.57, gamma=0.0)  # 22x22 matrix
```

It also includes the parity.
```python
irreps = Irreps("0e + 0o")  # an even scalar and an odd scalar
irreps.D_from_angles(alpha=0.0, beta=0.0, gamma=0.0, k=1)  # the matrix that applies parity
# DeviceArray([[ 1.,  0.],
#              [ 0., -1.]], dtype=float32)
```

## Shared weights

`torch` version:
```python
f = o3.FullyConnectedTensorProduct(irreps1, irreps2, irreps3, shared_weights=True)

f(x, y)
```

`jax` version:
```python
tp = FullyConnectedTensorProduct(irreps1, irreps2, irreps3)
w = [jax.random.normal(key, i.path_shape) for i in tp.instructions if i.has_weight]
f = jax.vmap(tp.left_right, (None, 0, 0), 0)
f = jax.jit(f)

f(w, x, y)
```

## Batch weights

`torch` version:
```python
f = o3.FullyConnectedTensorProduct(irreps1, irreps2, irreps3, shared_weights=False)

f(x, y, w)
```

`jax` version:
```python
tp = FullyConnectedTensorProduct(irreps1, irreps2, irreps3)
w = [jax.random.normal(key, (10,) + i.path_shape) for i in tp.instructions if i.has_weight]
f = jax.vmap(tp.left_right, (0, 0, 0), 0)
f = jax.jit(f)

f(w, x, y)
```

## Extra channel index

`torch` version not implemented

`jax` version just needs an extra bunch of `vmap` calls:
```python
def compose(f, g):
    return lambda *x: g(f(*x))

def tp_extra_channels(irreps_in1, irreps_in2, irreps_out):
    tp = FullyConnectedTensorProduct(irreps_in1, irreps_in2, irreps_out)

    f = tp.left_right
    f = jax.vmap(f, (0, None, None), 0)  # channel_out
    f = jax.vmap(f, (0, None, 0), 0)  # channel_in2
    f = jax.vmap(f, (0, 0, None), 0)  # channel_in1
    f = compose(f, lambda z: jnp.sum(z, (0, 1)) / jnp.sqrt(z.shape[0] * z.shape[1]))
    tp.left_right = f

    return tp

tp = tp_extra_channels(irreps, irreps, irreps)
f = jax.vmap(tp.left_right, (None, 0, 0), 0)  # batch
f = jax.jit(f)

w = [jax.random.normal(k, (16, 32, 48) + i.path_shape) for i in tp.instructions if i.has_weight]
# x1.shape = (batch, ch_in1, irreps_in1)
# x2.shape = (batch, ch_in2, irreps_in2)
z = f(w, x1, x2)
# z.shape = (batch, ch_out, irreps_out)
```
