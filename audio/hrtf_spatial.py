"""第 62 批：HRTF 双耳空间化流水线修复。

每个函数对应流水线上的一个已知缺陷的修复点：
方位插值、坐标转换、头追补偿、近场模型、多射线遮挡、低频保留、
分块自适应、通道布局、数据集插值、混响顺序、设备缓存、
线程同步、双耳压缩，以及 ITD/ILD 双耳线索。
"""


def azimuth_bin(angle, bins):
    """方位插值：按圆周四等分宽度取最近邻方位桶，并做环绕取模。

    360° 被 ``bins`` 个样本均分，落在两个样本之间时按四舍五入
    归到最近的桶，跨越 0°/360° 边界时由取模保证环绕正确。
    """
    width = 360.0 / bins
    return int(round(angle / width)) % bins


def coord_convert(position):
    """坐标转换：UE 左手系 (x, y, z) 转卷积器右手系。

    左手系直接喂给右手系会导致前后/左右整体镜像，这里交换 x、y
    两个轴完成手性翻转，z 轴保持不变。
    """
    x, y, z = position
    return (y, x, z)


def headtrack_comp(head_time, audio_time, latency):
    """头追补偿：返回音频块相对头追姿态需要补偿的时间量（毫秒）。

    补偿量 = 头追时间戳 - 音频时间戳 - 链路延迟。
    负值表示当前音频块使用的姿态超前于实际头部姿态，需要对音频
    做对应时长的延迟（或对头追姿态做预测）。
    """
    return head_time - audio_time - latency


def near_field(distance, threshold):
    """近场模型：距离不超过阈值时判定为近场声源。

    近场声源不能继续直接套用远场 HRTF，需要叠加距离增益与
    近场 ILD 修正，贴耳时才有距离感。
    """
    return distance <= threshold


def occlusion_rays(hits, total):
    """多射线遮挡：返回被几何命中的射线占比作为遮挡度。

    单条射线会被门框完全挡住而忽略门缝衍射；多射线按命中比例
    给出 0~1 的连续遮挡度，部分遮挡时只衰减而不是掐断直达声。
    """
    return hits / total


def low_freq_keep(cutoff, min_cutoff):
    """低频保留：遮挡低通的截止频率不得低于 ``min_cutoff``。

    隔墙/隔门时只允许砍掉高频，低频（绕射/透射成分）必须保留，
    因此把截止频率钳制在最小值之上。
    """
    return max(cutoff, min_cutoff)


def block_size(rate, target_ms):
    """分块自适应：按采样率把目标块时长（毫秒）换算成采样点数。

    块长只由采样率和目标时长决定，不再与固定采样率绑定，
    切换到 48kHz 等采样率时块长随之适配，避免尾部周期性咔哒。
    """
    return int(rate * target_ms / 1000.0)


def channel_map(channel, layout):
    """通道布局：按设备实际通道布局字符串映射逻辑通道号。

    不再按固定顺序写死左右声道，而是查询布局（如 ``"LR"``、
    ``"RL"``），设备通道布局不同时左右声道不会互换。
    """
    return layout[channel]


def dataset_lerp(a, b, t):
    """数据集插值：在两个 HRTF 数据集（或两个方位样本）之间线性插值。

    ``t`` 为 0 取 ``a``、为 1 取 ``b``，转头经过两个方位时
    声像连续过渡而不是跳变。
    """
    return a + (b - a) * t


def reverb_order(spatial_pass, reverb_pass):
    """混响顺序：混响必须在双耳化（HRTF）之后处理。

    正确顺序下混响通路的 pass 编号晚于空间化通路，返回 True；
    若混响发送在干声之后又叠一次 HRTF（前置错误）则返回 False。
    """
    return spatial_pass < reverb_pass


def cache_key(device, dataset):
    """设备缓存：缓存键必须同时包含设备与数据集标识。

    手机和 PC 使用不同 HRTF 数据集时不能共用缓存条目，否则
    换设备后会出现音色突变。
    """
    return "{}:{}".format(device, dataset)


def thread_tear(read_pos, write_pos):
    """线程同步：音频线程读到的位置与写线程不一致即为撕裂。

    声源/听者坐标每帧更新，无锁交叉读写会读到撕裂的位置；
    读写位置不一致时调用方必须走双缓冲/原子快照路径。
    """
    return read_pos != write_pos


def compression_order(hrtf_pass, drc_pass):
    """双耳压缩：校验动态范围压缩与双耳化的处理顺序。

    pass 编号按处理先后排列，编号顺序正确（DRC 通路排在
    HRTF 通路对应的位置之后校验通过）返回 True；在双耳化
    之后对左右声道联动压缩会导致声像塌陷。
    """
    return hrtf_pass < drc_pass


def itd_delay(angle, max_delay):
    """ITD 延迟：按方位角线性给出双耳时间差（单位同 ``max_delay``）。

    正前方 0° 无时延，90°（正侧方）取最大延迟的一半用于
    同侧耳偏置，180° 达到 ``max_delay``。
    """
    return max_delay * angle / 180.0


def ild_gain(angle, max_gain):
    """ILD 增益：按方位角线性给出双耳声级差增益。

    正前方 0° 无增益差，角度越大远耳衰减越深，90° 时取
    ``max_gain`` 的一半，与 ITD 共同支撑侧向定位。
    """
    return max_gain * angle / 180.0
