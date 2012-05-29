
#ifndef HEAD_TRACKING_H
#define HEAD_TRACKING_H
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/surface/mls.h>
#include <pcl/registration/ia_ransac.h>
#include <pcl/registration/icp_nl.h>
#include <pcl/segmentation/extract_clusters.h>

#include <hrl_head_tracking/pcl_basic.h>
#include <hrl_head_tracking/skin_color_util.h>
#include <hrl_head_tracking/hsl_rgb_conversions.h>

typedef pcl::KdTree<PRGB> KDTree;

#define COPY_PT_INTO_CLOUD(source, dest, ind) \
do { \
    PRGB pt; \
    pt.x = source->points[ind].x; pt.y = source->points[ind].y; pt.z = source->points[ind].z; \
    pt.rgb = source->points[ind].rgb; \
    dest->points.push_back(pt); \
} while(0)

#define PT_IS_NOT_NAN(pc, ind) ( (pc)->points[(ind)].x == (pc)->points[(ind)].x && \
                                 (pc)->points[(ind)].y == (pc)->points[(ind)].y && \
                                 (pc)->points[(ind)].z == (pc)->points[(ind)].z  )

void extractSkinPC(const PCRGB::Ptr& pc_in, PCRGB::Ptr& pc_out, double thresh);
uint32_t findClosestPoint(const PCRGB::Ptr& pc, uint32_t u, uint32_t v);
void sphereTrim(const PCRGB::Ptr& pc_in, PCRGB::Ptr& pc_out, uint32_t ind, double radius);

#endif