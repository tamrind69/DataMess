"""
Migration: add ratings.mess_id and update unique constraint.

Run once:
    py -3.12 -m uv run python migrate_add_rating_mess.py

Verify with:
    py -3.12 -m uv run python migrate_add_rating_mess.py  # second run is a no-op
"""

from sqlalchemy import text
from app.db.session import engine


def run() -> None:
    with engine.begin() as conn:
        # ── Step 0: Check current schema state for idempotency / partial migration ──
        col_info = conn.execute(
            text(
                "SELECT is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'ratings' "
                "  AND column_name = 'mess_id'"
            )
        ).fetchone()

        has_mess_id = col_info is not None
        is_not_null = col_info is not None and col_info[0] == "NO"

        # Verify foreign key on ratings.mess_id specifically references public.messes(id)
        fk_row = conn.execute(
            text(
                "SELECT tc.constraint_name "
                "FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                "  AND tc.table_schema = kcu.table_schema "
                "JOIN information_schema.constraint_column_usage ccu "
                "  ON tc.constraint_name = ccu.constraint_name "
                "  AND tc.table_schema = ccu.constraint_schema "
                "WHERE tc.table_schema = 'public' "
                "  AND tc.table_name = 'ratings' "
                "  AND tc.constraint_type = 'FOREIGN KEY' "
                "  AND kcu.column_name = 'mess_id' "
                "  AND ccu.table_schema = 'public' "
                "  AND ccu.table_name = 'messes' "
                "  AND ccu.column_name = 'id'"
            )
        ).fetchone()
        has_fk = fk_row is not None
        fk_name = fk_row[0] if fk_row else None

        new_uq = conn.execute(
            text(
                "SELECT constraint_name "
                "FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'ratings' "
                "  AND constraint_type = 'UNIQUE' "
                "  AND constraint_name = 'uq_rating_user_dish_mess'"
            )
        ).fetchone()
        has_new_uq = new_uq is not None

        old_uq = conn.execute(
            text(
                "SELECT constraint_name "
                "FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'ratings' "
                "  AND constraint_type = 'UNIQUE' "
                "  AND constraint_name = 'uq_rating_user_dish'"
            )
        ).fetchone()
        has_old_uq = old_uq is not None

        if has_mess_id:
            # If mess_id already exists, check whether migration is complete or partial
            is_fully_migrated = (
                has_mess_id
                and is_not_null
                and has_fk
                and has_new_uq
                and not has_old_uq
            )

            status_report = [
                f"  - Column public.ratings.mess_id exists: True",
                f"  - public.ratings.mess_id is NOT NULL: {is_not_null}",
                f"  - Foreign key public.ratings.mess_id → public.messes(id): {'Yes (' + fk_name + ')' if has_fk else 'Missing'}",
                f"  - Unique constraint 'uq_rating_user_dish_mess': {'Present' if has_new_uq else 'Missing'}",
                f"  - Legacy constraint 'uq_rating_user_dish' dropped: {not has_old_uq}",
            ]

            if is_fully_migrated:
                print("ratings.mess_id already exists and is fully migrated:")
                print("\n".join(status_report))
                print("\n✓ Migration previously completed successfully. Nothing to do.")
                return

            # Partially migrated schema detected
            report_str = "\n".join(status_report)
            raise RuntimeError(
                f"Partially migrated schema detected on table 'public.ratings':\n{report_str}\n"
                "Refusing to proceed automatically. Please resolve the partial schema manually."
            )

        # ── Fresh migration ──────────────────────────────────────────────────────────
        print("Step 1: Adding column public.ratings.mess_id (nullable)…")
        conn.execute(text("ALTER TABLE public.ratings ADD COLUMN mess_id INTEGER"))

        print("Step 2: Adding FK constraint ratings_mess_id_fkey → public.messes(id)…")
        conn.execute(
            text(
                "ALTER TABLE public.ratings "
                "ADD CONSTRAINT ratings_mess_id_fkey "
                "FOREIGN KEY (mess_id) REFERENCES public.messes(id)"
            )
        )

        # ── Step 3: Inspect ratings before backfilling ────────────────────────────────
        null_count = conn.execute(
            text("SELECT COUNT(*) FROM public.ratings WHERE mess_id IS NULL")
        ).scalar()
        print(f"Step 3: Found {null_count} rating row(s) requiring mess assignment.")

        if null_count > 0:
            # Inspect dish occurrences across messes
            dish_mess_stats = conn.execute(
                text(
                    "SELECT "
                    "    r.id AS rating_id, "
                    "    r.dish_id, "
                    "    COUNT(DISTINCT mn.mess_id) AS mess_count "
                    "FROM public.ratings r "
                    "LEFT JOIN public.menu_items mi ON mi.dish_id = r.dish_id "
                    "LEFT JOIN public.menus mn ON mn.id = mi.menu_id "
                    "WHERE r.mess_id IS NULL "
                    "GROUP BY r.id, r.dish_id "
                    "ORDER BY r.id"
                )
            ).fetchall()

            zero_mess_rating_ids = [row.rating_id for row in dish_mess_stats if row.mess_count == 0]
            multi_mess_rating_ids = [row.rating_id for row in dish_mess_stats if row.mess_count > 1]

            if zero_mess_rating_ids or multi_mess_rating_ids:
                error_lines = ["Cannot backfill ratings.mess_id due to ambiguous dish-mess mapping:"]
                if zero_mess_rating_ids:
                    error_lines.append(
                        f"  - {len(zero_mess_rating_ids)} rating(s) whose dishes occur in ZERO mess menus: IDs {zero_mess_rating_ids}"
                    )
                if multi_mess_rating_ids:
                    error_lines.append(
                        f"  - {len(multi_mess_rating_ids)} rating(s) whose dishes occur in MULTIPLE distinct messes: IDs {multi_mess_rating_ids}"
                    )
                error_lines.append(
                    "Migration stopped safely. Data must be reviewed manually before backfilling. Rolling back."
                )
                raise RuntimeError("\n".join(error_lines))

            # Backfill unambiguous ratings to their single associated mess
            print("Step 3a: Backfilling ratings to their unique associated mess…")
            conn.execute(
                text(
                    "UPDATE public.ratings r "
                    "SET mess_id = sub.mess_id "
                    "FROM ( "
                    "    SELECT mi.dish_id, mn.mess_id "
                    "    FROM public.menu_items mi "
                    "    JOIN public.menus mn ON mn.id = mi.menu_id "
                    "    GROUP BY mi.dish_id, mn.mess_id "
                    ") sub "
                    "WHERE r.dish_id = sub.dish_id "
                    "  AND r.mess_id IS NULL"
                )
            )

        # ── Step 4: Verify no NULL mess_id remain before setting NOT NULL ────────────
        remaining_nulls = conn.execute(
            text("SELECT id FROM public.ratings WHERE mess_id IS NULL ORDER BY id")
        ).scalars().all()
        if remaining_nulls:
            raise RuntimeError(
                f"Validation failed: {len(remaining_nulls)} rating(s) still have NULL mess_id: IDs {remaining_nulls}. "
                "Cannot set mess_id to NOT NULL. Rolling back."
            )

        print("Step 4: Setting public.ratings.mess_id to NOT NULL…")
        conn.execute(text("ALTER TABLE public.ratings ALTER COLUMN mess_id SET NOT NULL"))

        # ── Step 5: Validate uniqueness before constraint replacement ────────────────
        duplicates = conn.execute(
            text(
                "SELECT user_id, dish_id, mess_id, COUNT(*) AS cnt "
                "FROM public.ratings "
                "GROUP BY user_id, dish_id, mess_id "
                "HAVING COUNT(*) > 1"
            )
        ).fetchall()
        if duplicates:
            dup_list = [
                f"(user_id={d[0]}, dish_id={d[1]}, mess_id={d[2]}, count={d[3]})"
                for d in duplicates
            ]
            raise RuntimeError(
                f"Validation failed: Found duplicate ratings for the same (user_id, dish_id, mess_id): {dup_list}. "
                "Cannot add constraint uq_rating_user_dish_mess. Rolling back."
            )

        print("Step 5: Dropping legacy constraint 'uq_rating_user_dish' if present…")
        if has_old_uq:
            conn.execute(text("ALTER TABLE public.ratings DROP CONSTRAINT uq_rating_user_dish"))
        else:
            conn.execute(text("ALTER TABLE public.ratings DROP CONSTRAINT IF EXISTS uq_rating_user_dish"))

        print("Step 6: Adding unique constraint 'uq_rating_user_dish_mess'…")
        conn.execute(
            text(
                "ALTER TABLE public.ratings "
                "ADD CONSTRAINT uq_rating_user_dish_mess "
                "UNIQUE (user_id, dish_id, mess_id)"
            )
        )

        print("\n✓ Migration complete.")


if __name__ == "__main__":
    run()
