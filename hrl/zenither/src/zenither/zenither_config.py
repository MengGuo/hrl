
calib = {
    'El-E': {
        'robot': 'El-E',
        'pos_factor': 0.9144 / (183897 - 1250),
        'vel_factor': 0.9144 / (183897 - 1250) / 20,
        'acc_factor': 0.9144 / (183897 - 1250),
        'POS_MAX': 0.9,
        'VEL_DEFAULT': 1.5,
        'VEL_MAX': 4.0,
        'ACC_DEFAULT':0.0002,
        'ACC_MAX':0.001,
        'ZERO_BIAS':-0.004,
        'HAS_BRAKE':True,
        'nadir_torque': 0,
        'zenith_torque': 200,
        'down_fast_torque': 0,
        'down_slow_torque': 50,
        'down_snail_torque': 60,
        'up_fast_torque': 300,
        'up_slow_torque': 250,
        'up_snail_torque': 200,
        'max_height': 0.89,
        'min_height': 0.005
        },
    'HRL2': {
        #-------- Cressel's explanation -------------------------
        # max speed for size 40 1m actuator is 1400rpm / 0.45m/s
        # conversion for velocity 536.87633 cnts/s / rpm
        # 536.87633*1400/0.45 # cnts/s / m/s (0.5,-540179)(0.0,0)
        # close but not there yet

        #-------- Advait's explanation
        # 1 rev of zenither = 20mm (from festo manual)
        # 1 rev of animatics servo = 2000 encoder counts (pg 6, section 1.0 of the animatics manual)
        # a gear reduction of 10 (I think I remember Cressel mentioning this).
        # => 20000 counts = 20mm or 1 count = 1/1000,000 meters
        #

        'robot': 'HRL2',
        'pos_factor': 1.0/ (-1000000), # Advait - Apr 27, 2009
        'vel_factor': 1.0/ ( -1082996 - (-8))/20,
        'acc_factor': 1.0/ ( -1082996 - (-8)),
        'POS_MAX': 0.96, # Advait - Feb 17, 2009
        'VEL_DEFAULT': 0.025,
        'VEL_MAX': 0.45,
        'ACC_DEFAULT':0.0002,
        'ACC_MAX':0.001,
        'ZERO_BIAS':0.28,
        'HAS_BRAKE':True,
        'nadir_torque': 1,
        'zenith_torque': 400,
        'down_fast_torque': 0,
        'down_slow_torque': 3,
        'down_snail_torque': 5,
        'up_fast_torque': 450,
        'up_slow_torque': 400,
        'up_snail_torque': 300,
        'zero_vel_torque': 90,
        'max_height': 1.3,
        'min_height': 0.29
        }
}


