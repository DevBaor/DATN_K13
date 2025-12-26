<?php

namespace App\Http\Controllers\Api\KhachThue;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class RecommendationController extends Controller
{
    /**
     * Ask the scoring server to fetch candidates from DB, compute awards and return
     * ordered IDs + awards. Then return full post objects ordered by award.
     */
    public function recommend(Request $request)
    {
        try {
            $user = $request->user();

            $flaskUrl = env('DQN_SCORE_SERVER', 'http://127.0.0.1:8002/score');

            // Ask server to fetch and score up to 100 candidates (server will limit/optimize)
            // include token header if configured in this Laravel app's .env
            $headers = [];
            $dqnToken = env('DQN_SCORE_TOKEN');
            if ($dqnToken) {
                $headers['X-DQN-Token'] = $dqnToken;
                $headers['Accept'] = 'application/json';
            }

            $client = Http::withHeaders($headers)->timeout(15);
            $resp = $client->post($flaskUrl, [
                'fetch' => true,
                'limit' => 100,
                'user_id' => $user ? $user->id : null,
            ]);

            if ($resp->failed()) {
                Log::warning('RecommendationController: score server returned error', ['status' => $resp->status(), 'body' => $resp->body()]);
                // fallback: return recent posts (limit 50)
                $fallback = DB::table('bai_dang as bd')
                    ->join('phong as p', 'p.id', '=', 'bd.phong_id')
                    ->join('day_tro as d', 'd.id', '=', 'p.day_tro_id')
                    ->where('bd.trang_thai', 'dang')
                    ->where('p.trang_thai', '<>', 'bao_tri')
                    ->select('bd.*')
                    ->orderByDesc('bd.ngay_tao')
                    ->limit(50)
                    ->get();

                return response()->json([ 'success' => true, 'data' => $fallback ]);
            }

            $decoded = $resp->json();
            if (!is_array($decoded) || count($decoded) == 0) {
                return response()->json([ 'success' => true, 'data' => [] ]);
            }

            // decoded is array of { id, award, base_award, pref_match }
            $ids = array_map(function($r) { return intval($r['id']); }, $decoded);

            // fetch full post records for these ids
            $posts = DB::table('bai_dang as bd')
                ->join('phong as p', 'p.id', '=', 'bd.phong_id')
                ->join('day_tro as d', 'd.id', '=', 'p.day_tro_id')
                ->whereIn('bd.id', $ids)
                ->select(
                    'bd.id as bai_dang_id', 'bd.tieu_de', 'bd.mo_ta', 'bd.gia_niem_yet',
                    'p.id as phong_id', 'p.dien_tich', 'p.suc_chua', 'd.dia_chi', 'd.tien_ich'
                )
                ->get()
                ->keyBy('bai_dang_id')
                ->toArray();

            // Re-order posts to follow order from scoring server and attach award
            $result = [];
            foreach ($decoded as $r) {
                $bid = intval($r['id']);
                $post = isset($posts[$bid]) ? $posts[$bid] : null;
                if ($post) {
                    $post->award = $r['award'];
                    $result[] = $post;
                }
            }

            // limit to top 50
            $top = array_slice($result, 0, 50);
            return response()->json([ 'success' => true, 'data' => $top ]);

        } catch (\Throwable $e) {
            Log::error('RecommendationController: exception during inference loop', ['exception' => $e->getMessage()]);
            return response()->json([
                'success' => false,
                'message' => 'Inference failed (exception)',
                'error' => $e->getMessage(),
            ], 500);
        }
    }
}
