import cv2
import numpy as np

from guimauve.detection.detector import Detector


class FeatureMatching(Detector):
    def compute(self, needle, haystack, target, params):
        n_features = params["n_features"]
        contrast_threshold = params["contrast_threshold"]
        edge_threshold = params["edge_threshold"]
        sigma = params["sigma"]
        lowe_ratio = params["lowe_ratio"]
        min_points = params["min_points"]
        ransac_threshold = params["ransac_threshold"]
        ratio_tolerance = params["ratio_tolerance"]
        size_tolerance = params["size_tolerance"]

        # Preprocessing
        if len(needle.shape) == 3:
            needle = cv2.cvtColor(needle, cv2.COLOR_BGR2GRAY)
        if len(haystack.shape) == 3:
            haystack = cv2.cvtColor(haystack, cv2.COLOR_BGR2GRAY)

        h_n, w_n = needle.shape[:2]
        target_ratio = w_n / h_n

        # SIFT Detection
        detector = cv2.SIFT_create(
            nfeatures=n_features, contrastThreshold=contrast_threshold, edgeThreshold=edge_threshold, sigma=sigma
        )

        kp_n, des_n = detector.detectAndCompute(needle, None)
        kp_h, des_h = detector.detectAndCompute(haystack, None)

        # Mathematical safety: at least 4 points for homography
        effective_min_pts = max(min_points, 4)

        results = []

        if des_n is None or des_h is None or len(kp_h) < effective_min_pts:
            return results

        curr_kp_h, curr_des_h = list(kp_h), des_h.copy()
        bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

        for _ in range(15):
            if len(curr_kp_h) < effective_min_pts:
                break

            matches = bf.knnMatch(des_n, curr_des_h, k=2)
            good = [m[0] for m in matches if len(m) == 2 and m[0].distance < lowe_ratio * m[1].distance]

            if len(good) < effective_min_pts:
                break

            src_pts = np.float32([kp_n[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([curr_kp_h[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

            H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, ransac_threshold)

            if H is None or np.sum(mask) < effective_min_pts:
                break

            # Geometric Analysis
            pts_n = np.float32([[0, 0], [w_n, 0], [w_n, h_n], [0, h_n]]).reshape(-1, 1, 2)
            dst_raw = cv2.perspectiveTransform(pts_n, H)

            vec_w = dst_raw[1][0] - dst_raw[0][0]
            vec_h = dst_raw[2][0] - dst_raw[1][0]
            rw, rh = np.linalg.norm(vec_w), np.linalg.norm(vec_h)

            if rh == 0 or rw == 0:
                break

            current_ratio = rw / rh
            # STABILIZATION: Use the average of both scales to prevent squashing
            current_scale = (rw / w_n + rh / h_n) / 2

            # Verification of physical constraints
            valid_ratio = (
                (target_ratio * (1 - ratio_tolerance)) < current_ratio < (target_ratio * (1 + ratio_tolerance))
            )
            valid_size = (1 - size_tolerance) < current_scale < (1 + size_tolerance)
            valid_convex = cv2.isContourConvex(dst_raw.astype(np.int32))

            if valid_ratio and valid_size and valid_convex:
                m = cv2.moments(dst_raw)
                if m["m00"] > 1.0:  # Non-zero area
                    cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
                    angle = np.arctan2(vec_w[1], vec_w[0])

                    # Perfect box based on stabilized scale
                    final_w, final_h = w_n * current_scale, h_n * current_scale
                    rect = np.array(
                        [
                            [-final_w / 2, -final_h / 2],
                            [final_w / 2, -final_h / 2],
                            [final_w / 2, final_h / 2],
                            [-final_w / 2, final_h / 2],
                        ]
                    )

                    R = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
                    dst_corners = [(p @ R.T + [cx, cy]).astype(int) for p in rect]

                    # Recalculated target point
                    f_pt = (np.array([target[0] - w_n / 2, target[1] - h_n / 2]) * current_scale) @ R.T + [cx, cy]
                    results.append((dst_corners, tuple(f_pt.astype(int)), 1.0))

            # Spatial Cleanup
            curr_kp_h, curr_des_h = self._cleanup_zone(H, w_n, h_n, curr_kp_h, curr_des_h)

        return results

    @staticmethod
    def _cleanup_zone(H, w, h, kps, des):
        pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
        dst = cv2.perspectiveTransform(pts, H)
        rect = cv2.boundingRect(dst.astype(np.int32))
        x, y, wr, hr = rect
        m = 5
        keep = [
            i for i, kp in enumerate(kps) if not (x - m <= kp.pt[0] <= x + wr + m and y - m <= kp.pt[1] <= y + hr + m)
        ]
        return [kps[i] for i in keep], des[keep]
