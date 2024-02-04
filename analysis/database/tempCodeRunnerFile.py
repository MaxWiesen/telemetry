
        # Checks if low/min was passed by name, but not high/max which would cause low/min to be treated as high/max
        if ('low' in kwargs or 'min' in kwargs) and 'high' not in kwargs and 'max' not in kwargs:
            raise ValueError('min/low number specified, but max/high number was not.')

        # Checks if as_scalar matches size. If size > 1, a scalar cannot contain the values
        if as_scalar and size != 1:
            raise ValueError('as_scalar was set to true, but more than 1 value was expected to be returned.')

        # If point, return a tuple of longitude and latitude
        if dtype == 'point':
            res = [self.get_random_data(float, 1, as_scalar=True, low=-180, high=180),
                   self.get_random_data(float, 1, as_scalar=True, low=-90, high=90)]
        # If bool or int, use default_rng.integers method with some argument manipulation
        elif dtype is bool or np.issubdtype(dtype, np.integer):
            res = self.rng.integers(0, 2 if dtype is bool else 32767, size=size, dtype=dtype)
        # If float, use default_rng.random method with [0, 1) --> [low/min, high/max) transformation algorithm
        elif np.issubdtype(dtype, np.floating):
            # Algorithm used is (big - small) * random(0-1) + small
            res = (kwargs.get('high', kwargs.get('max', 1)) - kwargs.get('low', kwargs.get('min', 0))) * \
                self.rng.random(size, dtype) + kwargs.get('low', kwargs.get('min', 0))
        # If str, bacon
        elif dtype is str:
            res = [requests.get('https://baconipsum.com/api/',
                                params={'type': 'meat-and-filler', 'sentences': kwargs.get('length', 10),
                                        'start-with-lorem': 1}).text[2:-2] for _ in range(size)]
        else:
            raise NotImplementedError(f'Data type {dtype} not implemented yet.')

        return res[0] if size == 1 else list(res)


def main():
    client = mosquitto_connect('paho_tester')
    test = DataTester()
    table = 'dynamics'
    table_desc = get_table_column_sp